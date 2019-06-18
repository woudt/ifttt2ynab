# Install IFTTT2YNAB

This instruction will explain how to install IFTTT2YNAB on Google App Engine.
Of course, you are free to use any other place to host your installation.
In that case, see http://flask.pocoo.org/docs/1.0/deploying/ 

## Prerequisites

You need:
- A google account.
- A google cloud project. Create one at https://console.cloud.google.com/project 
  and note the project id (we will be using `ynab2ifttt-yourname` as an example
  in this document)
- A working installation of the Google Cloud SDK.
  Get it at https://cloud.google.com/sdk/docs/

During installation, you also need a working billing account on google cloud.
Normally, usage should stay within the free usage limits and for normal use the
free usage limits should be more than enough. Therefore you can disable billing
after installation to guarantee your bill will remain 0.

## Install IFTTT2YNAB

If your project id is `ynab2ifttt-yourname`, run the following commands in the
ifttt2ynab project directory.

    gcloud config set project ynab2ifttt-yourname
    gcloud app create --region us-central
    gcloud app deploy app

(you can change the region, but since YNAB is hosted on the west-coast and
IFTTT is hosted on the east-coast, this should give good results)

If all went well, your app should now be up and running at:
https://ynab2ifttt-yourname.appspot.com

You can now continue to configure IFTTT Platform.
See [CONFIG.md](CONFIG.md) for instructions.
