<!DOCTYPE html>
<html>
  <head>
    <link href="c3.css" rel="stylesheet" type="text/css">
    <link href="style.css" rel="stylesheet" type="text/css">
    <script src="d3.js" charset="utf-8"></script>
    <script src="c3.js"></script>
  </head>

  <body>
    <div style="text-align:center; font: 40px sans-serif; font-weight:bold">MooCloud Dashboard</div>
    <br><br>
    <div align="center">
      <div style="float:center; width:90%; background:#909090; color:white; font-size: 18px; padding-top:10px; padding-bottom:20px">
	<span style="font-size:20px;text-decoration:underline">Policy Selection</span>
	<br>
	<?php
if (isset($_POST['policy'])) {
    $policy = $_POST['policy'];
    $request = xmlrpc_encode_request("load", array($policy));
    $context = stream_context_create(array('http' => array(
	'method' => "POST",
	'header' => "Content-Type: text/xml",
	'content' => $request
    )));

    $file = file_get_contents("http://localhost:8000/", false, $context);
    $response = xmlrpc_decode($file);
    if ($response && xmlrpc_is_fault($response)) {
	$trigger_error("xmlrpc: $response[faultString] ($response[faultCode])");
    } else {
	if ($response[0] == 0) {
	    print_r($response);
	}
    }
} else {
    // get current
    $request = xmlrpc_encode_request("current", array());
    $context = stream_context_create(array('http' => array(
	'method' => "POST",
	'header' => "Content-Type: text/xml",
	'content' => $request
    )));

    $file = file_get_contents("http://localhost:8000/", false, $context);
    $response = xmlrpc_decode($file);
    if ($response && xmlrpc_is_fault($response)) {
	$trigger_error("xmlrpc: $response[faultString] ($response[faultCode])");
    } else {
	if ($response[0] == 0) {
	    echo "Error: . $response[0]";
	}

	$policy = $response[1];
    }
}
    ?>
	<br>
	<br>
	<form action="" method="post">
	  <input type="radio" name="policy" value="default"
		 <?php echo ($policy=='default')? 'checked' : '' ?>>Default
	  <br>
	  <input type="radio" name="policy" value="static"
		 <?php echo ($policy=='static')? 'checked' : '' ?>>Static
	  <br>
	  <input type="radio" name="policy" value="adaptive"
		 <?php echo ($policy=='adaptive')? 'checked' : '' ?>>Adaptive
	  <br>
	  <br>
	  <input type="submit" value="Update Policy">
	</div>
      <br>
    </div>
    <div style="margin: 0 auto; width:90%">
      <div align="center" style="width:50%; display:block; float:left">
	<?php
	   echo "<table>\n";
	   echo "<tr><th>VLAN</th><th>Tenant Type</th><th># Hosts</th></tr>";
	   $f = fopen("tenants.csv", "r");
	   while (($line = fgetcsv($f)) !== false) {
               echo "<tr>";
               foreach ($line as $cell) {
                   echo "<td>" . htmlspecialchars($cell) . "</td>";
               }
               echo "</tr>";
	   }
	   fclose($f);
	   echo "\n</table>";
       ?>
	<br>
	<div id="bwplot" style="width:300px; height:300px"></div>
	<br>
	<div id="tenantplot" style="width:300px; height:300px"></div>
	<br>
      </div>
      <div align="center" style="width:50%; display:block; float:left">
	<?php
	   echo "<table>\n";
	   echo "<tr><th>Host</th><th>VLAN</th><th>Role</th></tr>";
	   $f = fopen("roles.csv", "r");
	   while (($line = fgetcsv($f)) !== false) {
               echo "<tr>";
               foreach ($line as $cell) {
                   echo "<td>" . htmlspecialchars($cell) . "</td>";
               }
               echo "</tr>";
	   }
	   fclose($f);
	   echo "\n</table>";
       ?>
	<br>
	<div id="bwDonut" style="width:250px; height:250px"></div>
	<br>
	<div id="tenantDonut" style="width:250px; height:250px"></div>
	<br>
	<div id="drpPktDonut" style="width:250px; height:250px"></div>
      </div>
      <div align="center">
	<div id="mcplot" style="width:300px; height:300px"></div>
      </div>
    </div>
    <script src="script.js"></script>
  </body>
</html>
