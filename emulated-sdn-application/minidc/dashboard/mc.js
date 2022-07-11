var mstatData = [];

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

    mcplot.load({
	columns: mstatData
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

update();

