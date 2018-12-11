echo "Message Drop Single Failure Scenario"
echo "============================"
if [ $verbose -eq 0 ]; then
	make clean > /dev/null
	make > /dev/null
	./Application testcases/msgdropsinglefailure.conf > /dev/null
else
	make clean
	make
	./Application testcases/msgdropsinglefailure.conf
fi
joincount=`grep joined dbg.log | cut -d" " -f2,4-7 | sort -u | wc -l`
if [ $joincount -eq 100 ]; then
	grade=`expr $grade + 15`
	echo "Checking Join..................10/10"
else
	joinfrom=`grep joined dbg.log | cut -d" " -f2 | sort -u`
	cnt=0
	for i in $joinfrom
	do
		jointo=`grep joined dbg.log | grep '^ '$i | cut -d" " -f4-7 | grep -v $i | sort -u | wc -l`
		if [ $jointo -eq 9 ]; then
			cnt=`expr $cnt + 1`
		fi
	done
	if [ $cnt -eq 10 ]; then
		grade=`expr $grade + 15`
		echo "Checking Join..................15/15"
	else
		echo "Checking Join..................0/15"
	fi
fi
failednode=`grep "Node failed at time" dbg.log | sort -u | awk '{print $1}'`
failcount=`grep removed dbg.log | sort -u | grep $failednode | wc -l`
if [ $failcount -ge 9 ]; then
	grade=`expr $grade + 15`
	echo "Checking Completeness..........15/15"
else
	echo "Checking Completeness..........0/15"
fi