"""Deploy reviewed application artifacts; never migrates or enables a schedule implicitly."""
import argparse
import json
import subprocess


def command(*args, capture=False):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None).stdout


def outputs(stack):
    document=json.loads(command('aws','cloudformation','describe-stacks','--stack-name',stack,capture=True))
    return {row['OutputKey']:row['OutputValue'] for row in document['Stacks'][0]['Outputs']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--foundation',default='housing-foundation')
    parser.add_argument('--application',default='housing-app')
    parser.add_argument('--image',required=True)
    parser.add_argument('--schedule',choices=['ENABLED','DISABLED'],required=True)
    parser.add_argument('--credential-revision',default='1')
    parser.add_argument('--release',required=True)
    parser.add_argument('--cloudformation-role',help='Optional dedicated CloudFormation execution role ARN')
    parser.add_argument('--artifact-bucket',help='Existing SAM artifact bucket; otherwise SAM resolves its managed bucket')
    args=parser.parse_args()
    if not args.release.replace('-','').replace('_','').isalnum(): parser.error('Release must be alphanumeric with hyphens or underscores')
    foundation=outputs(args.foundation)
    keys=('PublicSubnet','PrivateSubnets','ApiSecurityGroup','JobSecurityGroup','DatabaseHost','AdminSecretArn','ApiSecretArn','IngestSecretArn','TrestleSecretArn','ArchiveBucket','WebBucket','AlertsTopicArn')
    params={key:foundation[key] for key in keys}
    params.update(PipelineImage=args.image,ScheduleState=args.schedule,CredentialRevision=args.credential_revision)
    command('sam','build','--use-container','--template-file','infra/application.yaml')
    extra=['--s3-bucket',args.artifact_bucket] if args.artifact_bucket else ['--resolve-s3']
    if args.cloudformation_role: extra+=['--role-arn',args.cloudformation_role]
    command('sam','deploy','--template-file','.aws-sam/build/template.yaml','--stack-name',args.application,*extra,'--capabilities','CAPABILITY_IAM','--no-fail-on-empty-changeset','--no-confirm-changeset','--parameter-overrides',*[f'{key}={value}' for key,value in params.items()])
    app=outputs(args.application)
    destination=f"s3://{foundation['WebBucket']}"
    command('npm','ci','--prefix','web')
    command('npm','run','build','--prefix','web')
    # Keep immutable assets so existing tabs and the previous index remain usable.
    command('aws','s3','sync','web/dist/assets',destination+'/assets','--cache-control','public,max-age=31536000,immutable')
    command('aws','s3','sync','web/dist/geo',destination+'/geo','--cache-control','public,max-age=86400')
    command('aws','s3','cp','web/dist/index.html',destination+f'/releases/{args.release}/index.html','--cache-control','no-cache')
    command('aws','s3','cp','web/dist/index.html',destination+'/index.html','--cache-control','no-cache')
    command('aws','cloudfront','create-invalidation','--distribution-id',app['DistributionId'],'--paths','/index.html','/','/geo/*','/api/*')
    print('Released:',app['WebsiteUrl'])


if __name__=='__main__': main()
