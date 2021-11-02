from __future__ import print_function
import datetime
import io
import logging
import os
import sys
import time
import json
import math
from itertools import groupby

import azure.batch.batch_service_client as batch
import azure.batch.models as batchmodels


from azure.common.credentials import ServicePrincipalCredentials
from azure.batch import models
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

sys.path.append('.')
sys.path.append('..')
from msrestazure.azure_active_directory import ServicePrincipalCredentials
import adal, uuid, time

# Update the Batch and Storage account credential strings in config.py with values
# unique to your accounts. These are used when constructing connection strings
# for the Batch and Storage client objects.



def print_batch_exception(batch_exception):
    """
    Prints the contents of the specified Batch exception.

    :param batch_exception:
    """
    logging.info('-------------------------------------------')
    logging.info('Exception encountered:')
    if batch_exception.error and \
            batch_exception.error.message and \
            batch_exception.error.message.value:
        logging.info(batch_exception.error.message.value)
        if batch_exception.error.values:
            logging.info('')
            for mesg in batch_exception.error.values:
                logging.info('{}:\t{}'.format(mesg.key, mesg.value))
    logging.info('-------------------------------------------')




def add_tasks(batch_service_client, job_id, startval, multiplier, numloops,maxTaskBatch,linux,containerImage):
    """
    Adds a task for each input file in the collection to the specified job.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID of the job to which to add the tasks.
    :param list input_files: A collection of input files. One task will be
     created for each input file.
    :param output_container_sas_token: A SAS token granting write access to
    the specified Azure Blob storage container.
    """

    logging.info('Adding {} tasks to job [{}]...')

        # fpath = task_id + '/output.txt'

    tasks = list()
    count = 0
    #simulating more tasks
    for x in range(int(startval), (int(numloops)+1)):
        count += 1

        #command = "cmd /c \"C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\EXCEL.EXE\" %AZ_BATCH_APP_PACKAGE_excelSqlWrite#3.0%\\testvba2.xlsm"
        command = "cmd /c \"C:\\Program Files\\Python39\\python.exe\" %AZ_BATCH_APP_PACKAGE_piecalc#1.0%\\pie.py " + str(startval*(multiplier*count))
        commandLinux = "/bin/bash -c \"python3 /pie.py "+ str(startval*(multiplier*count)) + "\" "
        logging.debug("The value of counter is: "+ str(count)+ " command is: "+ str(command))
        
        user = batchmodels.UserIdentity(auto_user=batchmodels.AutoUserSpecification(elevation_level=batchmodels.ElevationLevel.admin, scope=batchmodels.AutoUserScope.pool))
        applicationpackage = batchmodels.ApplicationPackageReference(application_id='piecalc',version='1.0')
        if containerImage:
            task_container_settings = batchmodels.TaskContainerSettings(image_name=containerImage )
        # TBD handle the use case of windows containers / linux no containers 
        if linux:
            tasks.append(batch.models.TaskAddParameter(
                id='Task{}'.format(count),
                command_line=commandLinux,
                user_identity=user,
                container_settings=task_container_settings
            )
        )
        else:
            tasks.append(batch.models.TaskAddParameter(
                id='Task{}'.format(count),
                command_line=command,
                user_identity=user,
                application_package_references=[applicationpackage]
            )
        )
        if math.remainder(count, maxTaskBatch)== 0:
            logging.info("Submitting a batch of tasks for job ID " +str(job_id)+ ". Tasks will be submitted every " + str(maxTaskBatch) + ".  Currently submitting tasks up to " +str(count))
            batch_service_client.task.add_collection(job_id, tasks)
            tasks = list()

def create_job(batch_service_client, job_id, pool_id,displayName,priority):
    """
    Creates a job with the specified ID, associated with the specified pool.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID for the job.
    :param str pool_id: The ID for the pool.
    """
    logging.info('Creating job [{}]...'.format(job_id))

    job = batch.models.JobAddParameter(
        display_name=displayName,
        priority=priority,
        id=job_id,
        pool_info=batch.models.PoolInformation(pool_id=pool_id),
        on_all_tasks_complete=batchmodels.OnAllTasksComplete.terminate_job,
        on_task_failure='performExitOptionsJobAction')

    batch_service_client.job.add(job)


def update_job_to_terminate(batch_service_client, job_id):
    """
    Updates a job to terminate

    """
    logging.info('Updating job [{}]...'.format(job_id))

    jobpatch = batch.models.JobPatchParameter(

        on_all_tasks_complete='terminateJob'
        )

    batch_service_client.job.patch(job_id , jobpatch)

def wait_for_tasks_to_complete(batch_service_client, job_id, timeout):
    """
    Returns when all tasks in the specified job reach the Completed state.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The id of the job whose tasks should be to monitored.
    :param timedelta timeout: The duration to wait for task completion. If all
    tasks in the specified job do not reach Completed state within this time
    period, an exception will be raised.
    """
    timeout_expiration = datetime.datetime.now() + timeout

    logging.info("Monitoring all tasks for 'Completed' or  state, timeout in {}..."
          .format(timeout), end='')

    while datetime.datetime.now() < timeout_expiration:
        logging.info('.', end='')
        sys.stdout.flush()
        tasks = batch_service_client.task.list(job_id)

        incomplete_tasks = [task for task in tasks if
                            task.state != batchmodels.TaskState.completed]
        if not incomplete_tasks:
            logging.info('')
            return True
        else:
            time.sleep(1)

        if str(batch_service_client.job.get(job_id).state) == "JobState.completed":
            logging.info("Job Completed, so exiting")
            return True
        else:
            time.sleep(1)  


        

    logging.info('')
    raise RuntimeError("ERROR: Tasks did not reach 'Completed' state within "
                       "timeout period of " + str(timeout))


def connect_to_azure():
    # Create a Batch service client. We'll now be interacting with the Batch
    # service in addition to Storage
    credentials = DefaultAzureCredential()
    secret_client = SecretClient(vault_url="https://azbatchhpcgbbkv.vault.azure.net", credential=credentials)
    logging.info(secret_client)
    try:
        logging.info("About to connect to KV to retrieve secret ")
        #servicePrincipalClientID = secret_client.get_secret("AzureBatchServicePrincipalClientId")
        #servicePRincipalSecret= secret_client.get_secret("AzureBatchServicePrincipalSecret")
        servicePrincipalTenant= secret_client.get_secret("AzureBatchTenantID")
        logging.info("Tenant id retrieved from keyvault: "+servicePrincipalTenant)
    except:
        logging.info("An Exception occured connecting to keyvault, trying localsettings.json")
        servicePrincipalClientID =  os.environ["clientID"]
        servicePRincipalSecret= os.environ["secret"]
        servicePrincipalTenant= os.environ["tenant"]


    logging.info("Tenant id of keyvault: "+servicePrincipalTenant)



    credential = ServicePrincipalCredentials(tenant=servicePrincipalTenant,
    client_id=servicePrincipalClientID, 
    secret=servicePRincipalSecret,
    resource='https://batch.core.windows.net/')
    batch_client = batch.BatchServiceClient(credential,
                                                 batch_url='https://azbatchhpcgbb.eastus.batch.azure.com')
    return batch_client

def submit_batch_job(jobID, taskstorun, loopsMultiplier,displayName,priority,maxTaskBatch,linux,poolID,containerImage):

    start_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('Sample start: {}'.format(start_time))
    logging.info('')

    batch_client = connect_to_azure()

    dateTimeObj = datetime.datetime.now()
    dateObj = dateTimeObj.date()    
    job_id = jobID
    pool_id = poolID
    
    # Create the job that will run the tasks.
    create_job(batch_client, job_id, pool_id,displayName,priority)

    try:
        # Add the tasks to the job.
        add_tasks(batch_client, job_id, 1,loopsMultiplier,taskstorun,maxTaskBatch,linux,containerImage)
    except batchmodels.BatchErrorException as err:
        print_batch_exception(err)
        raise

    # Print out some timing info
    end_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('')
    logging.info('Sample end: {}'.format(end_time))
    logging.info('Elapsed time: {}'.format(end_time - start_time))
    logging.info('')


def query_batch_status(jobID, verbose):

    start_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('Sample start: {}'.format(start_time))
    logging.info('')

    batch_client = connect_to_azure()
    tasksStateArray= []
    resultsDict =  {}
    
    # Get Job State
    currentJobStatus = batch_client.job.get(jobID)
    resultsDict["jobID"]=currentJobStatus.id
    resultsDict["jobState"]=currentJobStatus.state
  
    resultsDict["priority"]=currentJobStatus.priority
    resultsDict["displayName"]=currentJobStatus.display_name
    resultsDict["creationTime"]=str(currentJobStatus.creation_time)
    resultsDict["lastModifiedTime"]=str(currentJobStatus.last_modified)
    resultsDict["poolID"]=currentJobStatus.pool_info.pool_id
    resultsDict["priority"]=currentJobStatus.priority

    logging.info(currentJobStatus.id)
    logging.info(currentJobStatus.creation_time)
    logging.info(currentJobStatus.last_modified)
    logging.info(currentJobStatus.pool_info.pool_id)

    # Loop through the tasks and record state
    tasks = batch_client.task.list(jobID)
    for task in tasks:
        taskElement= dict(state=task.state, taskID=task.id,commandLine=task.command_line)
        tasksStateArray.append(taskElement)

    # sort all the elements in the aray based on state
    tasksStateArray.sort(key=lambda content: content['state'])
    
    # group all elements in the array by state and then loop through to count each state
    summary = groupby(tasksStateArray,key=lambda content: content["state"])
    for state, group in summary:
        stateCounter=0
        for content in group:
            stateCounter = stateCounter +1
        logging.info(state+" "+str(stateCounter))
        resultsDict[state]=(stateCounter)
    


    # If verbose output is asked for, each task status is returned along with the command line
    if verbose :
        taskCountsJSON = json.dumps(tasksStateArray)
    else:
        taskCountsJSON = json.dumps(resultsDict)
    
    
    end_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('')
    logging.info('Sample end: {}'.format(end_time))
    logging.info('Elapsed time: {}'.format(end_time - start_time))
    logging.info('')
    
    return taskCountsJSON

def terminate_batch_job(jobID):

    start_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('Sample start: {}'.format(start_time))
    logging.info('')

    batch_client = connect_to_azure()
    returnState = batch_client.job.delete(jobID)

    end_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('')
    logging.info('Sample end: {}'.format(end_time))
    logging.info('Elapsed time: {}'.format(end_time - start_time))
    logging.info('')
    
    return returnState

def delete_jobs_matching(displayName, jobState):

    start_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('Sample start: {}'.format(start_time))
    logging.info('')

    batch_client = connect_to_azure()
    
    jobList = batch_client.job.list(
        job_list_options=batchmodels.JobListOptions(
        expand='stats'
    ))
    deleteCounter = 0 
    for job in jobList:
        if job.state== jobState:
            if str(job.display_name).__contains__(displayName):
                logging.info('Found a match for '+job.display_name +' '+job.id +' so deleting')
                jobDelete = batch_client.job.delete(job.id)
                deleteCounter = deleteCounter+ 1 
            else:
                logging.info('Job Name: '+str(job.display_name) +' '+job.id +' does not match' +displayName +' so not deleting')
        else:
            logging.info('Job State is:' + str(job.state)+ '  does not match: ' + jobState+ ' - not deleting: '+ str(job.display_name)+' '+job.id )

    
    end_time = datetime.datetime.now().replace(microsecond=0)
    logging.info('')
    logging.info('Sample end: {}'.format(end_time))
    logging.info('Elapsed time: {}'.format(end_time - start_time))
    logging.info('')
    
    return ("Deletion Search Complete: "+ str(deleteCounter) +" jobs deleted ")
