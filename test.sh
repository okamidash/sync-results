#!/usr/bin/env sh
echo $1
DATESTAMP=$(date +%s)


upload () {
	bucket=$1
	file=$2

	host=10.0.10.1:9000
	s3_key='mango'
	s3_secret='mangomango'

	resource="/${bucket}/${file}"
	content_type="text/plain"
	date=`date -R`
	_signature="PUT\n\n${content_type}\n${date}\n${resource}"
	signature=`echo -en ${_signature} | openssl sha1 -hmac ${s3_secret} -binary | base64`

	curl -s -X PUT -T "${file}" \
		 -H "Host: $host" \
		 -H "Date: ${date}" \
		 -H "Content-Type: ${content_type}" \
		 -H "Authorization: AWS ${s3_key}:${signature}" \
		 http://$host${resource}
}

run () {
	DISKNAME=$1
	DISKMODEL=$(cat /sys/class/block/$DISKNAME/device/model)
	TESTNAME=$2
	echo "############"
	echo "Operating on $DISKNAME $DISKMODEL"
	echo "/mnt/${DISKNAME}p1/testdir"
	echo "############"
	sync
	RESULTFILE="R${TESTNAME}-${DATESTAMP}-${DISKNAME}.json"
	ETCDRESULTFILE="ETCD-${TESTNAME}-${DATESTAMP}-${DISKNAME}.txt"
	NOSYNCRESULTFILE="R${TESTNAME}-${DATESTAMP}-${DISKNAME}-NOSYNC.txt"
	DISKFILE="DRIVE-${DISKNAME}.txt"
	mkdir -p /mnt/${DISKNAME}p1/testdir

	smartctl -a /dev/$DISKNAME > DRIVE-$DISKNAME.txt
	FOUNDDISK=$(findmnt -T /mnt/${DISKNAME}p1 -o SOURCE -n -r | tr '/' ' ' | awk '{print $2}')
	if [ "${FOUNDDISK}" != "${DISKNAME}p1" ]; then
		echo "NOT MOUNTED PROPERLY: $DISKNAME not mounted to $FOUNDDISK"
		exit 1
	fi

	fio \
		--rw=write \
		--ioengine=sync \
		--fdatasync=1 \
		--directory=/mnt/${DISKNAME}p1/testdir \
		--size=22m \
		--loops=10 \
		--bs=2300 \
		--output-format=json+ \
		--name=$DISKNAME > $RESULTFILE
	fio \
		--rw=write \
		--ioengine=sync \
		--directory=/mnt/${DISKNAME}p1/testdir \
		--size=22m \
		--loops=10 \
		--output-format=json+ \
		--bs=2300 \
		--name=$DISKNAME > $NOSYNCRESULTFILE
	
	ETCDDIR=/mnt/${DISKNAME}p1/etcd
	echo "#### Running etcd tests ${ETCDDIR} ####"
	rm -rf ${ETCDDIR}
	mkdir -p ${ETCDDIR}/wal
	mkdir -p ${ETCDDIR}/data
	echo "Starting ETCD"
	etcd --force-new-cluster --data-dir $ETCDDIR/data --log-outputs /var/log/${DISKNAME} &
	sleep 10
	echo "Launching benchmark"
	~/go/bin/benchmark --target-leader  --conns=100 --clients=1000 put --key-size=8 --sequential-keys --total=100000 --val-size=256 > $ETCDRESULTFILE
	killall etcd
	
	upload results $ETCDRESULTFILE
	echo "==== finished (${DISKNAME}) ===="
}

for device in $(ls /dev/nvme*n1); do DEVSHORT=$(echo $device | tr '\/' ' ' | awk '{print $2}'); run "$DEVSHORT" "4KBLOCKS"; done