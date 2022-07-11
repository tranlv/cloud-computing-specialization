var mstatData = [];
var bwstatData = [];
var bwshareData = [];
var tenantshareData = [];
var tenantstatData = [];
var drpPktData = [];

var update = function() {
    d3.json("memstats.json", function(data) {
	mstatData = [];
	data.results.forEach(function(d, i) {
	    var item = [d.param];
	    d.val.forEach(function(j) {
		item.push(j);
	    });

	    mstatData.push(item);
	});
    });

    d3.json("bwplot.json", function(data) {
	bwstatData = [];
	data.results.forEach(function(d, i) {
	    var item = [d.param];
	    d.val.forEach(function(j) {
		item.push(j);
	    });

	    bwstatData.push(item);
	});
    });

    d3.csv("bwshare.csv", function(data) {
	bwshareData = [];
	data.forEach(function(d, i) {
	    var item = [d.host];
	    item.push(d.bwshare);
	    bwshareData.push(item)
	});

    });

    d3.json("tenantplot.json", function(data) {
	tenantstatData = [];
	data.results.forEach(function(d, i) {
	    var item = [d.param];
	    d.val.forEach(function(j) {
		item.push(j);
	    });

	    tenantstatData.push(item);
	});
    });

    d3.csv("tenantshare.csv", function(data) {
	tenantshareData = [];
	data.forEach(function(d, i) {
	    var item = [d.host];
	    item.push(d.bwshare);
	    tenantshareData.push(item)
	});
    });

    d3.csv("droppedpkts.csv", function(data) {
	drpPktData = [];
	data.forEach(function(d, i) {
	    var item = [d.sw];
	    item.push(d.dpkts);
	    drpPktData.push(item)
	});
    });

    mcplot.load({
	columns: mstatData
    });

    bwplot.load({
	columns: bwstatData
    });

    bwDonut.load({
	columns: bwshareData
    });

    tenantplot.load({
	columns: tenantstatData
    });

    tenantDonut.load({
	columns: tenantshareData
    });

    drpPktDonut.load({
	columns: drpPktData
    });

    setTimeout(update, 2000);
}

var mcplot = c3.generate({
    bindto: '#mcplot',
    data: {
	columns: mstatData
    },
    axis: {
	y: {
	     label: 'Page Load (ms)'
	}
    }
});

var bwplot = c3.generate({
    bindto: '#bwplot',
    data: {
	columns: bwstatData
    },
    axis: {
	y: {
	     label: 'Bytes'
	}
    }
});

var bwDonut = c3.generate({
    bindto: '#bwDonut',
    data: {
        columns: bwshareData,
	type: 'donut'
    },
    donut: {
        title: "bw share (tx)"
    }
});

var tenantplot = c3.generate({
    bindto: '#tenantplot',
    data: {
	columns: tenantstatData
    },
    axis: {
	y: {
	     label: 'Bytes'
	}
    }
});

var tenantDonut = c3.generate({
    bindto: '#tenantDonut',
    data: {
        columns: tenantshareData,
	type: 'donut'
    },
    donut: {
        title: "tenant share (tx)"
    }
});

var drpPktDonut = c3.generate({
    bindto: '#drpPktDonut',
    data: {
        columns: drpPktData,
	type: 'bar'
    },
    donut: {
        title: "sw dropped packets"
    },
    axis: {
	x: {
	    label: "#dropped pkts"
	},
	y: {
	    label: "switch"
	}
    }
});

update();

