"""Run and monitor a private-database operation through a temporary Fargate task."""
import argparse
import json
import time
from scripts.aws_release import command,outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['migrate','ingest','rollback'])
    parser.add_argument('--foundation',default='housing-foundation')
    parser.add_argument('--application',default='housing-app')
    parser.add_argument('--run-id')
    parser.add_argument('--end-month')
    parser.add_argument('--timeout-minutes',type=int,default=240)
    args=parser.parse_args()
    foundation=outputs(args.foundation); app=outputs(args.application)
    name='migration' if args.action=='migrate' else 'pipeline'
    task=app['MigrationTask' if args.action=='migrate' else 'IngestTask']
    cmd=['backend.bootstrap'] if args.action=='migrate' else ['backend.publish','rollback'] if args.action=='rollback' else ['backend.ingest']
    if args.action=='ingest':
        for key in ('run_id','end_month'):
            if getattr(args,key): cmd+=['--'+key.replace('_','-'),getattr(args,key)]
    network={'awsvpcConfiguration':{'subnets':[foundation['PublicSubnet']],'securityGroups':[foundation['JobSecurityGroup']],'assignPublicIp':'ENABLED'}}
    result=json.loads(command('aws','ecs','run-task','--cluster',app['Cluster'],'--task-definition',task,'--launch-type','FARGATE','--network-configuration',json.dumps(network),'--overrides',json.dumps({'containerOverrides':[{'name':name,'command':cmd}]}),capture=True))
    if result.get('failures') or not result.get('tasks'): raise RuntimeError('ECS could not dispatch the task; inspect ECS failures in the console')
    arn=result['tasks'][0]['taskArn']; print('Task:',arn,flush=True)
    deadline=time.monotonic()+args.timeout_minutes*60
    while time.monotonic()<deadline:
        task=json.loads(command('aws','ecs','describe-tasks','--cluster',app['Cluster'],'--tasks',arn,capture=True))['tasks'][0]
        if task['lastStatus']=='STOPPED':
            if not task.get('containers') or any(c.get('exitCode')!=0 for c in task['containers']):
                raise RuntimeError(f"Task failed. Inspect log group {app['JobLogGroup']}; {task.get('stopCode','unknown stop code')}")
            print('Completed successfully.'); return
        time.sleep(20)
    raise TimeoutError(f'Task remains active: {arn}. Inspect or stop it in ECS; this monitor does not terminate production work automatically.')


if __name__=='__main__': main()
