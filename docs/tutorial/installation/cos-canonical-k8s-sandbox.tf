module "cos" {
  source        = "git::https://github.com/canonical/observability//terraform/modules/cos"
  model_name    = "cos"
  channel       = "1/stable"
  s3_endpoint   = "http://{{IPADDR}}:8080"
  s3_password   = "secret-key"
  s3_user       = "access-key"
  loki_bucket   = "loki"
  mimir_bucket  = "mimir"
  tempo_bucket  = "tempo"
  ssc_channel   = "1/stable"
  anti_affinity = true
}
