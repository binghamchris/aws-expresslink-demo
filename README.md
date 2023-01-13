# AWS IoT ExpressLink and Device Shadow Demo
This repo provides the sample code for the demonstration performed at the AWS User Group meetup in Basel in January 2023. It's intended to work in conjunction with the [demo web app](https://github.com/binghamchris/aws-expresslink-demo-webapp) provided in a separate repo, and requires a physical AWS IoT ExpressLink Demo Badge to work.

## Repo Contents
### AWS IoT ExpressLink Demo Badge Code
The file `code.py` and the directory `lib` should be installed on the physical AWS IoT ExpressLink Demo Badge.
Please see the instructions in (`deploy/README.md`)[https://github.com/binghamchris/aws-expresslink-demo/blob/main/deploy/README.md] for information on how to configure the Demo Badge to use this code.

### `deploy` Directory
This directory contains the CloudFormation code for deploying the components of the demo in AWS. Please see (`deploy/README.md`)[https://github.com/binghamchris/aws-expresslink-demo/blob/main/deploy/README.md] for further information.

### `image_preproc` Directory
This directory contains code for preparing images for display on the Demo Badge's screen. It's not used in the demo and is included for reference only.