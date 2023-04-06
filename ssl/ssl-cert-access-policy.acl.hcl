# If you want to keep the policy file around for some reason, this is the snippet you want.
#
# Update 'path' below to the name of the variable that contains the
# SSL cert to give access to, and issue the following:
#
# nomad acl policy apply -namespace default -job <jobname> <jobname>-<certname>-policy ./thisfile.hcl
#
# (The policy can be called anything but need to be unique per job/cert.
#
namespace "default" {
  variables {
    path "ssl_certs/home_andvari_net" {
      capabilities = ["read", "list"]
    }
  }
}
