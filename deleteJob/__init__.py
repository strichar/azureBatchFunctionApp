import logging

import azure.functions as func

from createAzureBatchJob.python_batch_demo import terminate_batch_job


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
        jobDeleteStatus= terminate_batch_job(jobID)
        return func.HttpResponse(
             jobDeleteStatus,
             status_code=200
        )
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a jobID in the query string or in the request body for a personalized response.",
             status_code=200
        )
