# Sensor Dashboard
Dashboard for the sensor payload for Battle of the Rockets 2024.

To run, install requirements:

```
pip install -r requirements.txt
```

Modify `.env` to include the serial port to which the reciever feather is connected, for example `/dev/ttyACM0` on Linux, or `COM2` on Windows.

Finally, you can run the program with `python main.py`, and open the page in a browser.
