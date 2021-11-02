import logging

import azure.functions as func

from createAzureBatchJob.python_batch_demo import delete_jobs_matching


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    displayNameMatch = req.params.get('displayNameMatch')
    if not displayNameMatch:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            displayNameMatch = req_body.get('displayNameMatch')
            jobState= req_body.get('jobState')

    if displayNameMatch:
        jobDeleteStatus= delete_jobs_matching(displayNameMatch, jobState)        
        return func.HttpResponse(
            jobDeleteStatus,
            status_code=200
        )
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a jobID in the query string or in the request body for a personalized response.",
             status_code=200
        )
