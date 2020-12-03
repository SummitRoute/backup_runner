See blog post: https://summitroute.com/blog/2020/11/24/setting_up_personal_gsuite_backups_on_aws/

<img src="https://raw.githubusercontent.com/summitroute/backup_runner/master/docs/backup_architecture.png" alt="Backup architecture">

Setup
=====
```
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

Deploy
======
```
cdk deploy -c email=you@somewhere.com
```

Configure
=========
Once deployed, you'll need to spin up an EC2, connect to it, attach the EFS to it, create a `nightly.sh` script to perform your backup, and then you can terminate the EC2.
