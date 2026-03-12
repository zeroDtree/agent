cd docker
docker build --build-arg UID=1000 -t agent:1.0 . -f ubuntu24.dockerfile
cd -