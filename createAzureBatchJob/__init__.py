import logging
import uuid
import azure.functions as func

from createAzureBatchJob.python_batch_demo import submit_batch_job
from datetime import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    #logging.info('Retrieved JSON body')
    #logging.info(str(req.get_json()))

    message = req.get_body()
   
   
 

    tasksToRun = req.params.get('tasksToRun')
    
    if not tasksToRun:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:

            logging.info('Tasks:')
            tasksToRun = req_body.get('tasksToRun')           
            loopsMultiplier = req_body.get('loopsMultiplier')
            maxTaskBatch=req_body.get('maxTaskBatch')
    if tasksToRun:
        guid = uuid.uuid4()
        
        displayName=(req_body.get('displayName')+"_"+str(datetime.now()))
        priority = (req_body.get('priority'))
        linux = (req_body.get('linux'))
        poolID = (req_body.get('poolID'))
        container= (req_body.get('container'))
        if container:
            containerImage = (req_body.get('containerImage'))
        else:
            containerImage=None
        
        submit_batch_job(guid,tasksToRun,loopsMultiplier,displayName,priority,maxTaskBatch,linux,poolID,containerImage)
        return func.HttpResponse(f" {guid}")

    else:
        return func.HttpResponse(f"Received the message: {message}", status_code=200)

        
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

    