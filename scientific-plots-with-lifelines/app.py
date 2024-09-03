import json
import boto3
import ast
import os
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    try:
        actionGroup = event['actionGroup']
        function = event['function']
        parameters = event.get('parameters', [])

        if function == "plot_kaplan_meier":
            responseBody = handle_plot_kaplan_meier(parameters)
        elif function == "fit_survival_regression":
            responseBody = handle_fit_survival_regression(parameters)

        action_response = {
            'actionGroup': actionGroup,
            'function': function,
            'functionResponse': {
                'responseBody': responseBody
            }
        }

        return {'response': action_response, 'messageVersion': event['messageVersion']}

    except Exception as e:
        error_response = {
            'actionGroup': event.get('actionGroup', 'Unknown'),
            'function': event.get('function', 'Unknown'),
            'functionResponse': {
                'responseBody': {
                    "TEXT": {
                        "body": f"Unhandled error in lambda_handler: {str(e)}"
                    }
                }
            }
        }
        return {'response': error_response, 'messageVersion': event.get('messageVersion', 'Unknown')}

def handle_plot_kaplan_meier(parameters):
    try:
        biomarker_name, hazard_ratio, p_value, baseline, duration_baseline, event_baseline, condition, duration_condition, event_condition = extract_kaplan_meier_params(parameters)
        
        s3_bucket = os.environ['S3_BUCKET']
        
        duration_baseline = ast.literal_eval(duration_baseline)
        event_baseline = ast.literal_eval(event_baseline)
        duration_condition = ast.literal_eval(duration_condition)
        event_condition = ast.literal_eval(event_condition)
        
        baseline = '<=10' 
        condition = '>10'
        
        fig = plot_kaplan_meier(biomarker_name, baseline, duration_baseline, event_baseline, condition, duration_condition, event_condition)
        save_plot(fig, s3_bucket)
        
        return {
            "TEXT": {
                "body": "The plot_kaplan_meier function was called successfully!"
            }
        }
    except Exception as e:
        return {
            "TEXT": {
                "body": f"Error in plot_kaplan_meier: {str(e)}"
            }
        }

def handle_fit_survival_regression(parameters):
    try:
        bucket, key = extract_s3_params(parameters)
        s3 = boto3.client('s3')
        
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(obj['Body'].read().decode('utf-8'))
        summary = fit_survival_regression_model(data)
        
        return {
            "TEXT": {
                "body": f"The fit_survival_regression function was called successfully! Response summary: {summary}"
            }
        }
    except ClientError as e:
        return {
            "TEXT": {
                "body": f"Error accessing S3: {str(e)}"
            }
        }
    except Exception as e:
        return {
            "TEXT": {
                "body": f"Error in fit_survival_regression: {str(e)}"
            }
        }

def extract_kaplan_meier_params(parameters):
    param_dict = {param["name"]: param["value"] for param in parameters}
    return (
        param_dict.get("biomarker_name"),
        param_dict.get("hazard_ratio"),
        param_dict.get("p_value"),
        param_dict.get("baseline"),
        param_dict.get("duration_baseline"),
        param_dict.get("event_baseline"),
        param_dict.get("condition"),
        param_dict.get("duration_condition"),
        param_dict.get("event_condition")
    )

def extract_s3_params(parameters):
    param_dict = {param["name"]: param["value"] for param in parameters}
    return param_dict.get("bucket"), param_dict.get("key")

# Ensure that plot_kaplan_meier, save_plot, and fit_survival_regression_model 
# functions are defined here or imported