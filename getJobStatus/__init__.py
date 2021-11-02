import logging

import azure.functions as func

from createAzureBatchJob.python_batch_demo import query_batch_status


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    jobID = req.params.get('jobID')
    if not jobID:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            jobID = req_body.get('jobID')

    if jobID:
        jobTaskStatus= query_batch_status(jobID,req_body.get('verbose'))
        return func.HttpResponse(
             jobTaskStatus,
             status_code=200
        )
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a jobID in the query string or in the request body for a personalized response.",
             status_code=200
        )
