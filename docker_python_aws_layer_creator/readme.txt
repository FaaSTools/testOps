put requirements into requirements.txt
update docker_install.sh to use correct python version (same as the function using the layer, make sure dependencies support this python version)

then run runner.sh
should work for macos and linux
for windows you can just run all lines in docker_install.sh manually until line 4, after line 4 switch to docker_install.sh and continue with the rest of runner.sh afterwards
or fix the script yourself :P