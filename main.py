"""Module running a plotly server to take in the formatted serial packets."""

# pylint: disable=line-too-long

import os
from dash import dash, html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import serial
from dotenv import load_dotenv

load_dotenv()

app = dash.Dash(__name__)

ser = serial.Serial()
ser.port = os.getenv('SERIAL_PORT')  # Arduino serial port
ser.baudrate = 115200
ser.timeout = 10  # specify timeout when using readline()
ser.open()
if ser.is_open is True:
    print("\nSerial port open!")

# The position of the rocket from the data
location = [
    {'lat': 0.0, 'lon': 0.0}
]

# This stuff makes the actual map
fig_map = px.scatter_mapbox(
    location, lat='lat', lon='lon',
    color_discrete_sequence=["red"],
    zoom=16, height=500, width=500,
)
fig_map.update_traces(marker={"size": 12})
fig_map.update_layout(
    mapbox_style="white-bg",
    mapbox_layers=[{
        "below": 'traces',
        "sourcetype": "raster",
        "sourceattribution": "United States Geological Survey",
        "source": [
            "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
        ]}
    ],
    height=500, width=500,
    margin={"r": 0, "t": 0, "l": 0, "b": 0}
)

# Acceleration data
accel = {
    'x': [0.0] * 200,
    'y': [0.0] * 200,
    'z': [0.0] * 200
}
fig_accel = px.line(accel, y=['x', 'y', 'z'])
fig_accel.update_layout(
    height=500, width=500,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    yaxis_range=[-4,4]
)

# Pressure and Temperature Data
pt_val_graph = {
    'press': [0.0] * 200,
    'temp': [0.0] * 200,
}
pt_val = [0.0, 0.0]
fig_pt = px.line(pt_val_graph)
fig_pt.update_layout(
    height=500, width=400,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    yaxis_range=[0,1200]
)

app.layout = html.Div([
    html.H1('UNL Rocketry Payload Dashboard'),
    html.Hr(),
    html.Div([
        html.Div([
            html.H2("Position:"),
            html.Div(id='lat-lon-text', className='display_text'),
            dcc.Graph(id='map', figure=fig_map),
        ], className='data-box'),
        html.Div([
            html.H2("Acceleration:"),
            html.Div(id='accel-text', className='display_text'),
            dcc.Graph(id='accel', figure=fig_accel),
        ], className='data-box'),
        html.Div([
            html.H2("Pressure & Temperature:"),
            html.Div(id='pt-text', className='display_text'),
            dcc.Graph(id='pt', figure=fig_pt),
        ], className='data-box'),
    ], className='main-data'),
    dcc.Interval(
        id='gps-interval',
        interval=1000,  # in milliseconds
        n_intervals=0
    ),
    dcc.Interval(
        id='data-interval',
        interval=200,  # in milliseconds
        n_intervals=0
    ),
])


@app.callback(Output('map', 'figure'),
              Input('gps-interval', 'n_intervals'))
def update_map(interval):# pylint: disable=unused-argument
    """ Updates the map """
    new_map = px.scatter_mapbox(
        location, lat='lat', lon='lon',
        color_discrete_sequence=["red"], zoom=16,
    )
    new_map.update_traces(marker={"size": 12})
    new_map.update_layout(
        height=500, width=500,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        mapbox_style="white-bg",
        mapbox_layers=[{
            "below": 'traces',
            "sourcetype": "raster",
            "sourceattribution": "United States Geological Survey",
            "source": [
                "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
            ]
        }]
    )

    return new_map


@app.callback(Output('lat-lon-text', 'children'),
              Input('gps-interval', 'n_intervals'))
def update_lat_lon_text(interval):# pylint: disable=unused-argument
    """ Update lat-lon text """
    return [
        html.Span(f'Latitude: {location[0]['lat']:.6f}'),
        html.Span(f'Longitude: {location[0]['lat']:.6f}')
    ]


@app.callback(Output('accel-text', 'children'),
              Input('data-interval', 'n_intervals'))
def update_data(interval): # pylint: disable=inconsistent-return-statements,unused-argument
    """ Update data from serial port """
    ser.reset_input_buffer()
    try:
        line = ser.readline().strip()
    except: # pylint: disable=bare-except
        return

    if line in ('\n', b''):
        return

    line_as_list = line.split(b',')
    if len(line_as_list)  < 8:
        return

    try:
        location[0]['lat'] = float(line_as_list[1])
        location[0]['lon'] = float(line_as_list[2])

        pt_val[1] = float(line_as_list[4]) - 278
        pt_val[0] = float(line_as_list[5])

        x = float(line_as_list[6])
        y = float(line_as_list[7])
        z = float(line_as_list[8])
    except: # pylint: disable=bare-except
        return

    pt_val_graph['press'].append(pt_val[0])
    pt_val_graph['temp'].append(pt_val[1])

    pt_val_graph['press'] = pt_val_graph['press'][-200:]
    pt_val_graph['temp'] = pt_val_graph['temp'][-200:]

    accel['x'].append(x)
    accel['y'].append(y)
    accel['z'].append(z)

    accel['x'] = accel['x'][-200:]
    accel['y'] = accel['y'][-200:]
    accel['z'] = accel['z'][-200:]

    return [
        html.Span(f'X: {x:.2f}'),
        html.Span(f'Y: {y:.2f}'),
        html.Span(f'Z: {z:.2f}')
    ]


@app.callback(Output('accel', 'figure'),
              Input('data-interval', 'n_intervals'))
def update_accel(interval):# pylint: disable=unused-argument
    """ Update acceleration data """
    new_accel = px.line(accel)
    new_accel.update_layout(
        height=500, width=500,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        yaxis_range=[-4,4]
    )

    return new_accel


@app.callback(Output('pt-text', 'children'),
              Input('data-interval', 'n_intervals'))
def update_pt_text(interval): # pylint: disable=unused-argument
    return [
        html.Span(f'Pres: {pt_val[0]:.2f}mb'),
        html.Span(f'Temp: {pt_val[1]:.2f}°C'),
    ]


@app.callback(Output('pt', 'figure'),
              Input('data-interval', 'n_intervals'))
def update_pt(interval):# pylint: disable=unused-argument
    """ Update press&temp data """
    new_pt = px.line(pt_val_graph)
    new_pt.update_layout(
        height=500, width=400,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        yaxis_range=[0,1200]
    )

    return new_pt


if __name__ == '__main__':
    app.run(debug=True)
