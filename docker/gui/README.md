Docker GUI folder contains two example configurations you can enable when you want to run the DearPyGui application inside a container and display the GUI on your host.
Choose one of the approaches below and follow the instructions in this README.

1) X11 forwarding (Linux hosts)
   - Uses host X server socket (/tmp/.X11-unix) and DISPLAY env var.
   - Lightweight and fast but requires `xhost` permission adjustment.

   Usage:
   ```bash
   # on host:
   xhost +local:docker
   docker compose -f docker/gui/docker-compose.x11.yml up --build
   # after finished:
   xhost -local:docker
   ```

2) VNC / noVNC (cross-platform)
   - Container runs an X server + window manager + noVNC server.
   - Access the GUI in your browser at http://localhost:6080
   - Heavier image but works on macOS/Windows/remote servers.

   Usage:
   ```bash
   docker compose -f docker/gui/docker-compose.novnc.yml up --build
   # open http://localhost:6080 in browser (password: secret)
   ```

Notes:
 - The X11 approach requires a Linux host with a running X server. For Wayland users, consider using XWayland or the VNC approach.
 - The examples use the `pyoranris` source mounted into `/app/src` and will run `python -c "from pyoranris.app import main; main()"`.
