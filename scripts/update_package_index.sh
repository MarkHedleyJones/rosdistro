#! /bin/bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DISTRO="kinetic"
ALPINE_DOCKER_URL="https://raw.githubusercontent.com/at-wat/alpine-ros/master/$DISTRO-ros-core-alpine-with-custom-apk/"

# Grab the latest Docker image for alpine-ros
DOCKERFILE="Dockerfile"
ENTRYPOINT="ros_entrypoint.sh"
wget "$ALPINE_DOCKER_URL$DOCKERFILE" -O Dockerfile
wget "$ALPINE_DOCKER_URL$ENTRYPOINT" -O ros_entrypoint.sh

# Detect if the script is being run from elsewhere (no need to detect individually)
if [ "./manual_entries_base.yaml" -f ]; then
  cp "$DIR/manual_entries_base.yaml" .
  cp "$DIR/manual_entries_python.yaml" .
fi

echo "COPY manual_entries_python.yaml /" >> ./Dockerfile
echo "COPY manual_entries_base.yaml /" >> ./Dockerfile
echo "COPY package_filter.py /" >> ./Dockerfile
echo "RUN apk update" >> ./Dockerfile
chmod +x ./ros_entrypoint.sh

docker build -t rosdistro-image "$DIR"

rm Dockerfile ros_entrypoint.sh


if [ "$INTERACTIVE" -eq 0 ]; then
  # Start the contriner with mapped a user-id, a mapped output folders, and run the package_filter.py script
  docker run -it -v "$(dirname "$DIR")"/kinetic:/rosdistro/kinetic -v "$(dirname "$DIR")"/rosdep:/rosdistro/rosdep -u $(id -u):$(id -g) rosdistro-image:latest /package_filter.py "$DISTRO"
else
  docker run -it -v "$(dirname "$DIR")"/scripts/package_filter.py:/package_filter.py -v "$(dirname "$DIR")"/kinetic:/rosdistro/kinetic -v "$(dirname "$DIR")"/rosdep:/rosdistro/rosdep -u $(id -u):$(id -g) rosdistro-image:latest
fi

echo "Completed"
