# Deploy Minio and S3 Integrator

```{warning}
The Minio charm is not suitable for production usage. Instead, use [Charmed Ceph](https://ubuntu.com/ceph/docs) and follow [this guide](https://discourse.charmhub.io/t/tempo-ha-docs-how-to-use-ceph-backed-s3-storage-for-ha-charms/15740). 
```

Minio is a lightweight S3-compatible object storage system. In its 
single-node configuration, it is suitable for providing an S3 storage backend for certain charmed applications such as Tempo, Loki and Mimir. For more, see: https://min.io.

## Using a script

This is [a small python script](https://raw.githubusercontent.com/canonical/tempo-coordinator-k8s-operator/main/scripts/deploy_minio.py) that deploys `minio`, `s3-integrator`, configures them and provisions a bucket for you to use.

```bash
$ juju switch cos  # select the model where you have COS-lite deployed
$ sudo snap install astral-uv --classic  # this is how we recommend to run the script, but you're free to do it your way
$ curl https://raw.githubusercontent.com/canonical/tempo-coordinator-k8s-operator/main/scripts/deploy_minio.py -o deploy_minio.py

# review the script prior to executing it, then:
$ MINIO_BUCKET="tempo" uv run --with minio deploy_minio.py
```

Once the command exits zero, your storage is ready and you can integrate with the `s3` app.

## Using the CLI

### 1. Deploy Minio 

Deploy the `minio` charm. Tailor the strength of both `access-key` and `secret-key` to how exposed your environment is.

```{note}
The `secret-key` must be at least 8 characters long. If not, Minio will crash.
```

```bash
$ juju deploy minio \
    --channel edge \
    --trust \
    --config access-key=<access-key> \
    --config secret-key=<secret-key>
```

And wait for it to go to `active/idle`.

### 2. Deploy the S3 Integrator

```bash
$ juju deploy s3-integrator s3 \
    --channel edge \
    --trust 
```

Wait for the `s3` app to go to `blocked/idle`.
The `s3` app will go into `blocked` status until you run the `sync-s3-credentials` action to give it access to `minio`.

```bash
$ juju run s3/leader sync-s3-credentials \
    access-key=<access-key> \
    secret-key=<secret-key>
```

### 3. Add a bucket

#### Using the Minio UI

The simplest way to create a bucket is to use the Minio console UI. Obtain the Minio IP from the `juju status` output and then open `http://MINIO_IP:9001` in a browser using the `access-key` and `secret-key` you configured earlier as user and password respectively.

From there you should be able to create a bucket with a few clicks. See [this guide](https://thenewstack.io/how-to-create-an-object-storage-bucket-with-minio-object-storage/) for a step-by-step tutorial.


#### Using the Python SDK

Alternatively, you can use the Minio Python SDK.

```bash
$ pip install minio
```

Then execute this script:

```python
from minio import Minio

address = <minio/0 unit IP>
bucket_name = <bucket name>

mc_client = Minio(
    f"{address}:9000",
    access_key=<access-key>,
    secret_key=<secret-key>,
    secure=False,
)

found = mc_client.bucket_exists(bucket_name)
if not found:
    mc_client.make_bucket(bucket_name)
```

### 4. Integrate the S3 Integrator

Now give the `s3` app access to the bucket.

```
$ juju config s3 \
    endpoint=minio-0.minio-endpoints.<Juju model name>.svc.cluster.local:9000 \
    bucket=<bucket name>
```

Now the `s3` application is ready to provide the `s3` endpoint to any charm requiring it.


```{warning}
As of `rev 41` of `s3-integrator`, if multiple charms each require integration with different S3 buckets, you would need to deploy multiple `s3-integrator` applications — one per unique bucket, as each `s3-integrator` application can only have **one** set of unique bucket configurations: [see more](https://github.com/canonical/s3-integrator/issues/48).
```
