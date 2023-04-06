This is a simple setup for storing your SSL certs in nomad variables and using them in jobs.

This is not advised for production, consider using vault. STRONGLY consider using vault --
I'm not 100% on the specifics but my belief from scanning docs is that any of your nomad
nodes getting popped while using this setup will result in bad news all around.

Getting Your Keys Into Nomad
============================

First, you want to upload your certificate files into nomad. There's a script here to do that for
one certificate. It's assumed you use letsencrypt and have things in the directory format it uses.

Get the script set up:

```
cd letsencrypt-to-nomad-vars
virtualenv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python3 letsencrypt-to-nomad-vars.py --helpshort
```

This will give you an idea of any tweakables. It's assumed that:

  - You're running as a user who can read private key files out of /etc/letsencrypt/live (i.e probably root)
  - You have a valid NOMAD_TOKEN environment variable that's able to read and write any variables inside *ssl_certs/*
  - There's a nomad server joined to the cluster you care about running on localhost

If any of these aren't true, you might want to adjust *--letsencrypt_base* or *--nomad_server* (or indeed, *--nomad_ssl* and/or *--nomad_ssl_verify* if you require SSL).

If you're me, this command line looks like:

```
python3 letsencrypt-to-nomad-vers.py --export_cert=mylovelycert.mydomain.tld
```

This will ideally then grab the cert form your LE direcrory and put it into *ssl_certs/mylovelycert_mydomain_tld* (nomad doesn't like periods in variable names) -- variables are actually a list of key/value pairs, so it creates 'privkey' and 'chain' keys, containing what you mght expect.

Congratulations, you've now got another copy of your private key out there somewhere.

Giving Jobs Access to the Certs
===============================

By default no jobs have access to the certs -- unless you specify *--nomad_var_base=nomad/jobs/<myjob>* to the above script (jo have access to any vars inside that path by default). 

Otherwise, you have to add an acl policy to nomad to give a job access to this cert explicitly. There's a script here to do that if you don't care much about the details. Otherwise there's a snippet of HCL in [ssl-cert-access-policy.acl.hcl](ssl-cert-access-policy.acl.hcl) and a sample command line that you can squirrel away somewhere in your future plans for gitops or whatever.

To give *myjob* access to the cetificate you uploaded earlier, do this:

```
./grant_job_access_to_cert.sh myjob mylovelycert.mydomain.tld
```

This can be run without access to your local cert copies, it writes and inserts an acl into nomad. Nomad will maybe say something nice, and you're done!

Actually using Certificates
===========================

The easiest way of using these variables so the most kinds of jobs interact with them is to use a template inside the secrets
directory of the alloc.

Short version of thow to do this is to insert something like this inside the *task* stanza of your job definition:

```
   template {
     data = "{{ with nomadVar \"ssl_keys/mylovelycert_mydomain_tld\" }}{{ .privkey }}{{ end }}"
     destination = "secrets/mylovelycert.mydomain.tld-privkey.pem"
     change_mode = "signal"
     change_signal = "SIGHUP"
     perms = 700
   }
   template {
     data = "{{ with nomadVar \"ssl_keys/mylovelycert_mydomain_tld\" }}{{ .chain }}{{ end }}"
     destination = "secrets/mylovelycert.mydomain.tld-fullchain.pem"
     perms = 700
   }
```

In the parts of your job definition that define where certificates are, look in /secrets -- the 'destination' above is from the root of the alloc.

That's it!
