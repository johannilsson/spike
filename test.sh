#!/bin.sh

SAMPLES=$1

for i in $(seq $SAMPLES)
do
  echo Sample $i
  mkdir -p spike/_work/todo/sample-$i
  cp -R spike/_work/sample/* spike/_work/todo/sample-$i/.
  touch spike/_work/todo/sample-$i/done.txt
done
