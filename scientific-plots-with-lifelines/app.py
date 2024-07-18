
import json
from lifelines import KaplanMeierFitter
import plotly.graph_objects as go
import ast
import io
import kaleido
import boto3
import os
  
    

def fit_km(name, durations, event_observed):
    """ Fit Kaplan-Meier model to data and return a data frame """
    kmf = KaplanMeierFitter()
    kmf.fit(durations=durations, event_observed=event_observed, label=name)
    df = kmf.survival_function_.copy(deep=True)
    lo95 = f"{name}_lower_0.95"
    hi95 = f"{name}_upper_0.95"
    df[lo95] = kmf.confidence_interval_[lo95]
    df[hi95] = kmf.confidence_interval_[hi95]
    df.reset_index(inplace=True)
    print(df)
    return df


def plotly_km(df, name, line_color, fill_color, fig=None):
    """ Create a plotly figure for Kaplan-Meier, for a single KM model """
    if fig is None:
        fig = go.Figure()
    lo95 = f"{name}_lower_0.95"
    hi95 = f"{name}_upper_0.95"
    fig.add_traces([go.Scatter(x=df['timeline']
                            , y=df[name]
                            , line_color = line_color
                            , line_shape='hv'
                            , name = name
                            , showlegend=False)
                , go.Scatter(x = df['timeline']
                            , y = df[hi95]
                            , mode = 'lines'
                            , line_color = 'rgba(0,0,0,0)'
                            , showlegend = False
                            , line_shape='hv')
                    , go.Scatter(x = df['timeline']
                            , y = df[lo95]
                            , mode = 'lines'
                            , line_color = 'rgba(0,0,0,0)'
                            , name = f"95% CI {name}"
                            , fill='tonexty'
                            , fillcolor = fill_color
                            , line_shape='hv'
                            )
                    ])
    print('plot figure')
    return fig


def plot_kaplan_meier(biomarker_name:str
                      , baseline:str, duration_baseline:list, event_baseline:list
                      , condition:str, duration_condition:list, event_condition:list):
    """ Plot Kaplan-Meier comparing condition vs baseline """
    print("\nduration_baseline:")
    print(type(duration_baseline))
    print(duration_baseline)
    print("\nevent_baseline:")
    print(event_baseline)
    df_baseline = fit_km(baseline, duration_baseline, event_baseline)
    #print("\df_baseline:" + str(df_baseline))
    #print("\duration_condition:" + str(duration_condition))
    #print("\event_condition:" + str(event_condition))
    df_condition = fit_km(condition, duration_condition, event_condition)
    #print("\df_condition:" + str(df_condition))
    fig = plotly_km(df_baseline, baseline, line_color='rgba(0,0,255,1)', fill_color='rgba(0, 0, 255, 0.2)', fig=None)
    fig = plotly_km(df_condition, condition, line_color='rgba(255,140,0,1)', fill_color='rgba(255, 140, 0, 0.2)', fig=fig)
    fig.update_layout(title_text=f"{biomarker_name}\n"
                      , legend=dict(
                          yanchor="top"
                          , y=0.99
                          , xanchor="left"
                          , x=0.9
                          )
                      )
    
    return fig
    
def save_plot(fig,s3_bucket):
    img_data = io.BytesIO()
    fig.write_image(img_data, format='png')
    img_data.seek(0)
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(s3_bucket)
    invocationID = 1
    KEY = 'graphs/invocationID/' + str(invocationID) + '/KMplot.png' 
    bucket.put_object(Body=img_data, ContentType='image/png', Key=KEY)
    return

def lambda_handler(event, context):
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    for param in parameters:
        if param["name"] == "biomarker_name":
            biomarker_name = param["value"]
        if param["name"] == "hazard_ratio":
            hazard_ratio = param["value"]
        if param["name"] == "p_value":
            p_value = param["value"]
        if param["name"] == "baseline":
            baseline = param["value"]
        if param["name"] == "duration_baseline":
            duration_baseline = param["value"]
        if param["name"] == "event_baseline":
            event_baseline = param["value"]
        if param["name"] == "condition":
            condition = param["value"]
        if param["name"] == "duration_condition":
            duration_condition = param["value"]
        if param["name"] == "event_condition":
            event_condition = param["value"]
        print(os.environ['S3_BUCKET'])
        s3_bucket = os.environ['S3_BUCKET']
        
    print(type(duration_baseline))
    print(duration_baseline)
    duration_baseline = ast.literal_eval(duration_baseline)
    event_baseline = ast.literal_eval(event_baseline)
    duration_condition = ast.literal_eval(duration_condition)
    event_condition = ast.literal_eval(event_condition)
    print(type(duration_baseline))
    #duration_baseline = duration_baseline.tolist()
    #event_baseline = event_baseline.tolist()
    #duration_condition = duration_condition.tolist()
    #event_condition = event_condition.tolist()
    baseline = '<=10' 
    condition = '>10'
    # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
    fig = plot_kaplan_meier(biomarker_name,baseline, duration_baseline,event_baseline,condition,duration_condition,event_condition)
    save_plot(fig,s3_bucket)
    responseBody =  {
        "TEXT": {
            "body": "The function {} was called successfully!".format(function)
        }
    }

    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': responseBody
        }

    }

    dummy_function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(dummy_function_response))

    return dummy_function_response
