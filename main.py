""" A dashboard to display data from a rocket telemetry system """
from time import sleep

import usb.core
import usb.util
from dash import dash, html, dcc
from dash.dependencies import Input, Output
import plotly.express as px

# pylint: disable=line-too-long

app = dash.Dash(__name__)

OUT_VENDOR_INTERFACE = ((0) << 7) | ((2) << 5) | (1)
IN_VENDOR_INTERFACE = ((1) << 7) | ((2) << 5) | (1)

# find our device
usb_device = usb.core.find(idVendor=0x5e1f, idProduct=0x1e55)

# was it found?
if usb_device is None:
    raise ValueError('USB Device not found... plug it in!')

usb_device.set_configuration() # pyright: ignore
cfg = usb_device.get_active_configuration() # pyright: ignore
intf = cfg[(0, 0)]

# The rocket's packet data
packet = {
    'time': {
        'hours': 0,
        'minutes': 0,
        'seconds': 0,
        'microseconds': 0
    },
    'latitude': 40.806862,
    'longitude': -96.681679,
    'altitude': 0,
    'temperature': 0,
    'pressure': 0,
    'acceleration': {
        'x': 0,
        'y': 0,
        'z': 0,
    }
}

# This stuff makes the actual map
fig_map = px.scatter_mapbox(
    packet, lat='latitude', lon='longitude',
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

# Acceleration graph data
accel = {
    'x': [0.0] * 200,
    'y': [0.0] * 200,
    'z': [0.0] * 200
}
fig_accel = px.line(accel, y=['x', 'y', 'z'])
fig_accel.update_layout(
    height=500, width=500,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    yaxis_range=[-8.5,8.5]
)

# Pressure and Temperature graph data
pt_val_graph = {
    'press': [0.0] * 200,
    'temp': [0.0] * 200,
}
fig_pressure = px.line(pt_val_graph['press'])
fig_pressure.update_layout(
    height=500, width=400,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    yaxis_range=[0,1200]
)

fig_temperature = px.line(pt_val_graph['temp'])
fig_temperature.update_layout(
    height=500, width=400,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    yaxis_range=[0,1200]
)

app.layout = html.Div([
    html.H1('UNL Rocketry Payload Dashboard'),
    html.P(id='time'),
    html.Hr(),
    html.Div(id='dummy'),
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
            dcc.Graph(id='pressure', figure=fig_pressure),
            dcc.Graph(id='temperature', figure=fig_temperature),
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
        packet, lat='latitude', lon='longitude',
        color_discrete_sequence=["red"], zoom=16,
    )
    new_map.update_traces(marker={"size": 12})
    new_map.update_layout(
        autosize=True,
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
        html.Span(f'Latitude: {packet['latitude']:.6f}'),
        html.Span(f'Longitude: {packet['longitude']:.6f}')
    ]


@app.callback(Output('time', 'children'),
              Input('data-interval', 'n_intervals'))
def update_data(interval): # pylint: disable=inconsistent-return-statements,unused-argument
    """ Update data from serial port """

    # Get new data from the USB receiver
    try:
        usb_device.ctrl_transfer(OUT_VENDOR_INTERFACE, 100, 1, 0) # pyright: ignore
        sleep(0.1)
        packet_bytes = usb_device.ctrl_transfer(IN_VENDOR_INTERFACE, 200, 1, 0, 0x20) # pyright: ignore
    except Exception as exc: # pylint: disable=broad-exception-caught
        print(f"{exc}")
        return dash.no_update

    # Construct a packet from the incoming data
    global packet # pylint: disable=global-statement
    packet = {
        'time': {
            'hours': packet_bytes[0],
            'minutes': packet_bytes[1],
            'seconds': packet_bytes[2],
            'microseconds': int.from_bytes(packet_bytes[3:7], "little")
        },
        'latitude': int.from_bytes(packet_bytes[7:11], "little", signed=True) / 1_000_000,
        'longitude': int.from_bytes(packet_bytes[11:15], "little", signed=True) / 1_000_000,
        'altitude': int.from_bytes(packet_bytes[15:19], "little", signed=True),
        'temperature': (int.from_bytes(packet_bytes[19:21], "little") / 10) - 5,
        'pressure': int.from_bytes(packet_bytes[21:23], "little") / 10,
        'acceleration': {
            'x': int.from_bytes(packet_bytes[23:25], "little", signed=True) / 20,
            'y': int.from_bytes(packet_bytes[25:27], "little", signed=True) / 20,
            'z': int.from_bytes(packet_bytes[27:29], "little", signed=True) / 20,
        }
    }

    pt_val_graph['press'].append(packet['pressure'])
    pt_val_graph['temp'].append(packet['temperature'])

    pt_val_graph['press'] = pt_val_graph['press'][-200:]
    pt_val_graph['temp'] = pt_val_graph['temp'][-200:]

    accel['x'].append(packet['acceleration']['x'])
    accel['y'].append(packet['acceleration']['y'])
    accel['z'].append(packet['acceleration']['z'])

    accel['x'] = accel['x'][-200:]
    accel['y'] = accel['y'][-200:]
    accel['z'] = accel['z'][-200:]

    return html.Span(f'{packet['time']}')


@app.callback(Output('accel-text', 'children'),
              Input('data-interval', 'n_intervals'))
def update_accel_text(interval): # pylint: disable=inconsistent-return-statements,unused-argument
    """ Update the acceleration text """
    return [
        html.Span(f'X: {packet['acceleration']['x']:.2f}'),
        html.Span(f'Y: {packet['acceleration']['y']:.2f}'),
        html.Span(f'Z: {packet['acceleration']['z']:.2f}')
    ]

@app.callback(Output('accel', 'figure'),
              Input('data-interval', 'n_intervals'))
def update_accel(interval):# pylint: disable=unused-argument
    """ Update acceleration data """
    new_accel = px.line(accel)
    new_accel.update_layout(
        autosize=True,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        yaxis_range=[-8.5,8.5],
        xaxis={'showticklabels': False, 'title': ''},
    )

    return new_accel


@app.callback(Output('pt-text', 'children'),
              Input('data-interval', 'n_intervals'))
def update_pt_text(interval): # pylint: disable=unused-argument
    """ Update pressure and temperature data """
    return [
        html.Span(f'Pres: {packet['pressure']:.2f}mb'),
        html.Span(f'Temp: {packet['temperature']:.2f}°C'),
    ]


@app.callback(Output('pressure', 'figure'),
              Input('data-interval', 'n_intervals'))
def update_pressure(interval):# pylint: disable=unused-argument
    """ Update press&temp data """
    new_pressure = px.line(pt_val_graph['press'])
    new_pressure.update_layout(
        autosize=True,
        height=250,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        yaxis_range=[300,1250],
        xaxis={'showticklabels': False, 'title': ''},
        showlegend=False,
    )

    return new_pressure

@app.callback(Output('temperature', 'figure'),
              Input('data-interval', 'n_intervals'))
def update_temperature(interval):# pylint: disable=unused-argument
    """ Update press&temp data """
    new_temperature = px.line(pt_val_graph['temp'])
    new_temperature.update_traces(line_color='#ffaf79')
    new_temperature.update_layout(
        autosize=True,
        height=250,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        xaxis={'showticklabels': False, 'title': ''},
        showlegend=False,
    )

    return new_temperature

if __name__ == '__main__':
    app.run(debug=True)
