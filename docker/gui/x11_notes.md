X11 notes for different host OSes:

Linux:
 - Use Xorg/X11. Run `xhost +local:docker` before starting and `xhost -local:docker` after.
 - You can mount ~/.Xauthority to preserve authentication instead of allowing all local containers.

macOS:
 - Install XQuartz. In XQuartz Preferences -> Security enable 'Allow connections from network clients'.
 - Set DISPLAY to host:0 (for Docker Desktop use host.docker.internal:0). Example:
   export DISPLAY=host.docker.internal:0
 - Alternatively run GUI on host and keep backend in Docker (recommended).

Windows:
 - Use an X server like VcXsrv or Xming. Adjust DISPLAY accordingly and allow connections.
 - Simpler: run GUI locally and containerize only backend services.
