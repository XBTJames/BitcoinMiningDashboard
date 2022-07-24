#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 12 12:11:24 2022

@author: @XBTJames
"""

import dash
from dash import Dash, html, Input, Output, dcc
from hashrateindex import API
from resolvers import RESOLVERS
import pandas as pd
import plotly.express as px

API = API(host = 'https://api.hashrateindex.com/graphql', method = 'POST', key = 'KEY') #Here, replace the Key with your own key. Key "KEY" I highly doubt works.
RESOLVERS = RESOLVERS(df = True)

app = Dash(__name__)
server = app.server

efficiency_dict = {'S9': 98.0,
                   'S15': 57.0,
                   'S17': 55.0,
                   'M20S': 49.0,
                   'S17 Pro' : 40.0,
                   'M30S' : 38.0,
                   'S19': 34.0,
                   'M30S++': 31.0,
                   'S19 Pro': 29.5,
                   'S19 XP': 21.5
                   }
list_of_machines = ['S9', 'S15', 'S17', 'M20S', 'S17 Pro', 'M30S', 'S19', 'M30S++', 'S19 Pro', 'S19 XP']

th_dict = {'S9' : 14.0,
           'S15' : 28.0,
           'S17' : 56.0,
           'M20S' : 68.0,
           'S17 Pro' : 53.0,
           'M30S' : 86.0,
           'S19' : 95.0,
           'M30S++' : 112.0,
           'S19 Pro' : 110,
           'S19 XP' : 140.0
           }

app.layout = html.Div([
    html.Div([
        html.H1("@XBTJames Bitcoin Mining & Energy Dashboard - Data Courtesy of Luxor's HashrateIndex API"),
        html.Div([
            html.Main(id = 'live-update-hashprice'),
                  ], style = {'width':'48%', 'display':'inline-block'}),
        dcc.Interval(
            id='interval-component',
            interval=300*1000, # in milliseconds, so 60 seconds * 1,000 milisecond is a minute, 300 seconds is 5 minutes. I feel like 5 minutes is an appropriate time to update things. It's how frequently ERCOT updates.
            n_intervals=0
            ),
        html.Div([
            html.Main(id='live-update-difficulty'),
            ], style = {'width':'48%','float':'right', 'display':'inline-block'}),
        html.H2('Bitcoin ASIC Static Breakeven Days & Bitcoin ASIC Pricing in Sats/TH'),
        html.Div([
            dcc.Graph(id='ASICbreakeven'),
            ], style={'width':'48%','display':'inline-block'},),
        html.Div([
            dcc.Graph(id='ASICinSats'),
            ], style = {'width':'48%','float':'right','display':'inline-block'},),
       html.H2('ASIC Historical Profitability - Select your Machine and Power Cost'),
        html.Div([
           dcc.Dropdown(
               list_of_machines,
               'S9',
               id='mach',
               )
           ], style ={'width':'48%','display':'inline-block'}),
       html.Div([
           dcc.Dropdown(
               [0.02,0.04,0.06,0.08,0.1,0.12,0.14],
               0.04,
               id='power',
               )
           ], style ={'width':'48%', 'float':'right','display':'inline-block'}),
       html.Div([
           dcc.Graph(id='ASICprofit'),]),
       html.H2('ERCOT Hub and Load Zone Pricing'),
       html.Div([
           dcc.Graph(id='ERCOT')
           ])
        ])
    ])

@app.callback(Output('live-update-hashprice', 'children'), #This app.callback uses the interval component to ping the Hashrateindex API and pull the most recent Hashprice
              Input('interval-component', 'n_intervals'))
def updateHashprice(n):
    res = API.get_bitcoin_overview()
    resolved = RESOLVERS.resolve_get_bitcoin_overview(res)
    hashprice = float(resolved['hashpriceUsd'][0])
    timestamp = resolved.iloc[0][0]
    return [
        html.Span('Hashprice is USD ' + str(round(hashprice,2)) + ' Data current as of UTC time ' + str(timestamp))
        ]

@app.callback(Output('live-update-difficulty', 'children'), #This app.callback uses the interval component to ping the Hashrateindex API and pull the most recent difficulty adjustment
              Input('interval-component', 'n_intervals'))
def updateDifficulty(n):
    res = API.get_bitcoin_overview()
    resolved = RESOLVERS.resolve_get_bitcoin_overview(res)
    est_diff_adj = float(resolved['estDiffAdj'][0])
    return [
        html.Span('Estimated Difficulty Adjustment is ' + str(round(est_diff_adj,2)) + '%')
        ]


@app.callback(Output('ASICbreakeven','figure'), #this app.callback uses the interval to update the static breakeven chart
              Input('interval-component','n_intervals'))
def updateASICbreakeven(n):
    res = API.get_hashprice('_1_YEAR','USD')
    hashpriceDF = RESOLVERS.resolve_get_hashprice(res)
    res = API.get_asic_price_index('_1_YEAR','USD')
    ASICpriceDF = RESOLVERS.resolve_get_asic_price_index(res)
    dates = ASICpriceDF['time']
    hashpriceDF = hashpriceDF.set_index('timestamp')
    ASICpriceDF = ASICpriceDF.set_index('time')
    i = 0
    listofdates = []
    listofbreakevens = []
    listofmachines = []
    while i < len(dates):
        currenthashprice = hashpriceDF.loc[dates[i]]['usdHashprice']
        listofdates.append(dates[i])
        listofbreakevens.append((ASICpriceDF.loc[dates[i]]['under38']/currenthashprice))
        listofmachines.append('Under 38J/TH')
        listofdates.append(dates[i])
        listofbreakevens.append(ASICpriceDF.loc[dates[i]]['_38to68']/currenthashprice)
        listofmachines.append('38J/TH to 68J/TH')
        listofdates.append(dates[i])
        listofbreakevens.append(ASICpriceDF.loc[dates[i]]['above68']/currenthashprice)
        listofmachines.append('Above 68J/TH')
        i+=1
    dfASICbreakeven = pd.DataFrame()
    dfASICbreakeven['Date'] = listofdates
    dfASICbreakeven['Static Breakeven (days)'] = listofbreakevens
    dfASICbreakeven['ASIC Efficiency'] = listofmachines
    figASICbreakeven = px.line(dfASICbreakeven,x='Date',y='Static Breakeven (days)',color='ASIC Efficiency')
    return figASICbreakeven

@app.callback(Output('ASICinSats','figure'), #this app.callback uses the interval to update the ASIC pricing chart
              Input('interval-component','n_intervals'))
def updateASICinSats(n):
    res = API.get_asic_price_index('_1_YEAR','BTC')
    ASICdf = RESOLVERS.resolve_get_asic_price_index(res)
    ASICdf['time'] = pd.to_datetime(ASICdf['time'])
    ASICdf = ASICdf.set_index('time')

    dates= ASICdf.index.to_list()
    i = 0
    listofdates = []
    listofprices = []
    listofmachines = []
    while i < len(dates):
        currentunder38 = ASICdf.loc[dates[i]]['under38'] * 100000000
        current_38to68 = ASICdf.loc[dates[i]]['_38to68'] * 100000000
        currentabove68 = ASICdf.loc[dates[i]]['above68'] * 100000000
        listofdates.append(dates[i])
        listofprices.append(currentunder38)
        listofmachines.append('Under 38J/TH')
        listofdates.append(dates[i])
        listofprices.append(current_38to68)
        listofmachines.append('38J/TH to 68J/TH')
        listofdates.append(dates[i])
        listofprices.append(currentabove68)
        listofmachines.append('Above 68J/TH')
        i += 1
    
    ASICpricesinSats = pd.DataFrame()
    ASICpricesinSats['Date'] = listofdates
    ASICpricesinSats['ASIC Price (Sats per TH)'] = listofprices
    ASICpricesinSats['ASIC Efficiency'] = listofmachines
    
    figASICinSats = px.line(ASICpricesinSats,x='Date',y='ASIC Price (Sats per TH)',color='ASIC Efficiency')
    return figASICinSats

@app.callback(
    Output('ASICprofit','figure'),
    Input('mach','value'),
    Input('power','value'),
    Input('interval-component','n_intervals'))
def update_graph(machine_name,power,n):
    th = th_dict.get(machine_name)
    powerDraw = th * (efficiency_dict.get(machine_name) / 1000)
    dailyCost = powerDraw * power * 24
    res = API.get_hashprice('_1_YEAR','USD')
    df = RESOLVERS.resolve_get_hashprice(res)
    dates = df['timestamp']
    df = df.set_index('timestamp')
    i = 0
    profits = []
    while i < len(dates):
        r = th * df.loc[dates[i]]['usdHashprice']
        p = r - dailyCost
        profits.append(p)
        i+=1
    profitDF = pd.DataFrame()
    profitDF['Date'] = dates
    profitDF['Profitability (USD per Day)'] = profits
    fig = px.line(profitDF,x='Date',y='Profitability (USD per Day)')
    fig.update_layout(transition_duration=500)
    return fig

@app.callback(
    Output('ERCOT','figure'),
    Input('interval-component','n_intervals'))
def update_ercot(n):
    dfHUBS = pd.read_html('https://www.ercot.com/content/cdr/html/hb_lz.html')
    dfHUBS = dfHUBS[0]
    dfHUBS.columns = dfHUBS.loc[2]
    dfHUBS = dfHUBS.drop([0,1,2])
    dfHUBS['Price (USD per MWH)'] = pd.to_numeric(dfHUBS[dfHUBS.columns[3]])

    fig = px.bar(dfHUBS,x = 'Settlement Point', y = 'Price (USD per MWH)', text_auto=True)
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)