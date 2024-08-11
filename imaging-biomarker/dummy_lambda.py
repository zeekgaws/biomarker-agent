import json
import logging
import uuid
import boto3
import io
import pandas as pd

region='us-east-1'
account_id='942514891246'
sfn_statemachine_name = 'nsclc-radiogenomics-imaging-workflow-02e06b'


logger = logging.getLogger()
logger.setLevel("INFO")

def lambda_handler(event, context):
    logger.info(json.dumps(event))

    action = event["actionGroup"]
    function = event["function"]
    parameters = event["parameters"]
    print(parameters)
    
    if function == "compute_imaging_biomarker":
        subject_id = None
        for param in parameters:
            if param["name"] == "subject_id":
                subject_id = json.loads(param["value"])
                # subject_id = param["value"]
        if subject_id:
            suffix=uuid.uuid1().hex[:6] # to be used in resource names
            # suffix='dcd4788e327911efbca9be616a3e66ff'
            
            sfn = boto3.client('stepfunctions')

            sfn_statemachine_arn=f'arn:aws:states:{region}:{account_id}:stateMachine:{sfn_statemachine_name}'
            
            # input_data_bucket='sagemaker-solutions-prod-us-east-1'
            # input_data_prefix='sagemaker-lung-cancer-survival-prediction/1.1.0/data/nsclc_radiogenomics'
            # input_data_uri='s3://%s/%s' % (input_data_bucket, input_data_prefix)

            feature_store_name = 'imaging-feature-group-dcd4788e327911efbca9be616a3e66ff'
            processing_job_name = 'dcm-nifti-conversion-%s' % suffix

            output_data_uri=f's3://sagemaker-{region}:{account_id}/nsclc_radiogenomics'

            offline_store_s3uri = '%s/multimodal-imaging-featurestore' % output_data_uri

            payload = {
              "PreprocessingJobName": processing_job_name,
            #   "FeatureStoreName": feature_store_name,
            #   "OfflineStoreS3Uri": offline_store_s3uri,
              "Subject": subject_id
            }
            exeution_response = sfn.start_execution(stateMachineArn=sfn_statemachine_arn,
                                                    name=suffix,
                                                    input=json.dumps(payload))  
            
            logger.info(f"The function {function} was called successfully! StateMachine {exeution_response['executionArn']} has been started.")
            
            response_body =  {
                "TEXT": {
                    "body": f"Imaging biomarker processing has been submitted. Results can be retrieved from your database once the job {exeution_response['executionArn']} completes."
                }
            }
        session_attributes = {
        'sfn_executionArn': exeution_response['executionArn'],
        'imaging_biomarker_output_s3': output_data_uri
        }
    if function == "analyze_imaging_biomarker":
        subject_id = None
        result = []
        s3_client = boto3.client('s3')
        for param in parameters:
            if param["name"] == "subject_id":
                subject_id = json.loads(param["value"])
                # subject_id = param["value"]
                for id in subject_id:
                    output_data_uri=f's3://sagemaker-{region}-{account_id}/nsclc_radiogenomics/'
                    bucket_name=f'sagemaker-{region}-{account_id}'
                    object_key=f'nsclc_radiogenomics/CSV/{id}.csv'
                    # Download the CSV file from S3
                    try:
                        print(object_key)
                        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                        csv_data = response['Body'].read().decode('utf-8')
                    
                        # Load the CSV data into a Pandas DataFrame
                        df = pd.read_csv(io.StringIO(csv_data))
                        df['subject_id'] = id
                        # Print the first few rows of the DataFrame
                        print(df.head())
                        # Convert the DataFrame to JSON
                        json_data = df.to_json(orient='records')
        
                        print(json_data)
                        result = result + json.loads(json_data)
        
                    except Exception as e:
                        print(f'Error: {e}')
        
        response_body = {
        "TEXT": {
            'body':str(result)
        }
        }
    
    logger.info(f"Response body: {response_body}")

    function_response = {
        'actionGroup': action,
        'function': function,
        'functionResponse': {
            'responseBody': response_body
        }
    }
    
    session_attributes = {
        'imaging_biomarker_output_s3': output_data_uri
        }
    prompt_session_attributes = event['promptSessionAttributes']
    
    action_response = {
        'messageVersion': '1.0', 
        'response': function_response,
        'sessionAttributes': session_attributes,
        'promptSessionAttributes': prompt_session_attributes
    }
    
    logger.info(f"Action response: {action_response}")
    
    return action_response