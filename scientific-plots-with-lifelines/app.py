import json
import boto3
import ast
import os
from botocore.exceptions import ClientError
from lifelines import CoxPHFitter
from lifelines.exceptions import ConvergenceError
import pandas as pd
import plotly.graph_objects as go
import io

def lambda_handler(event, context):
    try:
        actionGroup = event['actionGroup']
        function = event['function']
        parameters = event.get('parameters', [])

        if function == "plot_kaplan_meier":
            responseBody = handle_plot_kaplan_meier(parameters)
        elif function == "fit_survival_regression":
            responseBody = handle_fit_survival_regression(parameters)
        else:
            responseBody = {
                "TEXT": {
                    "body": f"Unknown function: {function}"
                }
            }

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
    except ValueError as e:
        return {
            "TEXT": {
                "body": f"Error in plot_kaplan_meier: Invalid input data. {str(e)}"
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
    except ConvergenceError as e:
        return {
            "TEXT": {
                "body": f"Convergence error in survival regression model: {str(e)}. Please check your data for high collinearity or other issues."
            }
        }
    except ValueError as e:
        return {
            "TEXT": {
                "body": f"Invalid input data for survival regression model: {str(e)}"
            }
        }
    except Exception as e:
        return {
            "TEXT": {
                "body": f"Unexpected error in fit_survival_regression: {str(e)}"
            }
        }

def fit_survival_regression_model(data):
    try:
        records = data['Records']
        rows = []
        for row in records:
            rows.append([value.get(list(value.keys())[0]) for value in row])

        df = pd.DataFrame(rows)
        print(df)  # Keep this for debugging

        if df.empty:
            raise ValueError("The input DataFrame is empty.")

        if df.shape[1] < 2:
            raise ValueError("The DataFrame must have at least two columns for duration and event.")

        cph = CoxPHFitter()
        cph.fit(df, duration_col=1, event_col=0)
        summary = cph.summary
        return summary
    except ConvergenceError as e:
        print(f"Convergence Error: {str(e)}")
        raise
    except ValueError as e:
        print(f"Value Error in fit_survival_regression_model: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error in fit_survival_regression_model: {str(e)}")
        raise

def plot_kaplan_meier(biomarker_name, baseline, duration_baseline, event_baseline, condition, duration_condition, event_condition):
    try:
        from lifelines import KaplanMeierFitter

        kmf_baseline = KaplanMeierFitter()
        kmf_baseline.fit(duration_baseline, event_baseline, label=baseline)

        kmf_condition = KaplanMeierFitter()
        kmf_condition.fit(duration_condition, event_condition, label=condition)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=kmf_baseline.timeline, y=kmf_baseline.survival_function_.values.flatten(),
                                 mode='lines', name=baseline))
        fig.add_trace(go.Scatter(x=kmf_condition.timeline, y=kmf_condition.survival_function_.values.flatten(),
                                 mode='lines', name=condition))

        fig.update_layout(title=f'Kaplan-Meier Curve - {biomarker_name}',
                          xaxis_title='Time',
                          yaxis_title='Survival Probability')
        return fig
    except Exception as e:
        print(f"Error in plot_kaplan_meier: {str(e)}")
        raise

def save_plot(fig, s3_bucket):
    try:
        img_data = io.BytesIO()
        fig.write_image(img_data, format='png')
        img_data.seek(0)
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(s3_bucket)
        invocationID = 1  # You might want to generate this dynamically
        KEY = f'graphs/invocationID/{invocationID}/KMplot.png'
        bucket.put_object(Body=img_data, ContentType='image/png', Key=KEY)
    except Exception as e:
        print(f"Error in save_plot: {str(e)}")
        raise

def extract_kaplan_meier_params(parameters):
    param_dict = {param["name"]: param["value"] for param in parameters}
    required_params = ["biomarker_name", "hazard_ratio", "p_value", "baseline", "duration_baseline", "event_baseline", "condition", "duration_condition", "event_condition"]
    
    for param in required_params:
        if param not in param_dict:
            raise ValueError(f"Missing required parameter: {param}")

    return (param_dict["biomarker_name"], param_dict["hazard_ratio"], param_dict["p_value"],
            param_dict["baseline"], param_dict["duration_baseline"], param_dict["event_baseline"],
            param_dict["condition"], param_dict["duration_condition"], param_dict["event_condition"])

def extract_s3_params(parameters):
    param_dict = {param["name"]: param["value"] for param in parameters}
    if "bucket" not in param_dict or "key" not in param_dict:
        raise ValueError("Missing required S3 parameters: bucket and/or key")
    return param_dict["bucket"], param_dict["key"]

# Ensure that all necessary libraries are included in your Lambda deployment package