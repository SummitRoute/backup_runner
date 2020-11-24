See blog post: https://summitroute.com/blog/2020/11/24/setting_up_personal_gsuite_backups_on_aws/


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