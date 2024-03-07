# app.py

from dash import dash, html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import serial
import os
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
    zoom=16, height=500, width=700,
)
fig_map.update_traces(marker=dict(size=12))
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
    height=500, width=700,
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
    yaxis_range=[-3,3]
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
    ], className='main-data'),
    dcc.Interval(
        id='gps-interval',
        interval=1000,  # in milliseconds
        n_intervals=0
    ),
    dcc.Interval(
        id='data-interval',
        interval=500,  # in milliseconds
        n_intervals=0
    ),
])


@app.callback(Output('map', 'figure'),
              Input('gps-interval', 'n_intervals'))
def update_map(interval):
    fig_map = px.scatter_mapbox(
        location, lat='lat', lon='lon',
        color_discrete_sequence=["red"], zoom=16,
    )
    fig_map.update_traces(marker=dict(size=12))
    fig_map.update_layout(
        height=500, width=700,
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

    return fig_map


@app.callback(Output('lat-lon-text', 'children'),
              Input('gps-interval', 'n_intervals'))
def update_lat_lon_text(interval):
    return [
        html.Span('Latitude: {:.6f}'.format(location[0]['lat'])),
        html.Span('Longitude: {:.6f}'.format(location[0]['lon']))
    ]


@app.callback(Output('accel-text', 'children'),
              Input('data-interval', 'n_intervals'))
def update_(interval):
    ser.reset_input_buffer()
    try:
        line = ser.readline().strip()
    except:
        return

    if line == "\n" or line == b'':
        return

    line_as_list = line.split(b',')
    if len(line_as_list)  < 8:
        return

    try:
        location[0]['lat'] = float(line_as_list[1])
        location[0]['lon'] = float(line_as_list[2])

        x = float(line_as_list[6])
        y = float(line_as_list[7])
        z = float(line_as_list[8])
    except:
        return

    accel['x'].append(x)
    accel['y'].append(y)
    accel['z'].append(z)

    accel['x'] = accel['x'][-200:]
    accel['y'] = accel['y'][-200:]
    accel['z'] = accel['z'][-200:]

    return [
        html.Span('X: {:.2f}'.format(x)),
        html.Span('Y: {:.2f}'.format(y)),
        html.Span('Z: {:.2f}'.format(z))
    ]


@app.callback(Output('accel', 'figure'),
              Input('data-interval', 'n_intervals'))
def update_data(interval):
    fig_accel = px.line(accel)
    fig_accel.update_layout(
        height=500, width=500,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        yaxis_range=[-4,4]
    )

    return fig_accel

if __name__ == '__main__':
    app.run_server(debug=True)
