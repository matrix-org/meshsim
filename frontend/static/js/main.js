function hashString(str) {
		var hash = 0, i, chr;
		if (str.length === 0) return hash;
		for (i = 0; i < str.length; i++) {
				chr   = str.charCodeAt(i);
				hash  = ((hash << 5) - hash) + chr;
				hash |= 0; // Convert to 32bit integer
		}
		return hash;
};

const svg = d3.select("svg")

let data = {
		links: [],
		nodes: [],
};

let linksById = {};

let lastNodeId = 0;
let selectedLinkId = null;

var c10 = d3.scaleOrdinal(d3.schemeCategory10);

// init D3 drag support
const drag = d3.drag()
		.on('start', (d) => {
		})
		.on('drag', function(d) {
				data.nodes[d3.event.subject.name].x = d3.event.x;
				data.nodes[d3.event.subject.name].y = d3.event.y;

				d3.select(this)
						.attr("transform", `translate(${ d3.event.x }, ${ d3.event.y })`)

				updateLinks();
		})
		.on('end', (d) => {
				fetch(`/server/${d3.event.subject.name}/position`, {
						method: "PUT",
						headers: { 'Content-type': 'application/json '},
						body: JSON.stringify({ x: d3.event.subject.x, y: d3.event.subject.y }),
				}).then(r=>{
						fetchData();
				}).catch(function(error) {
						console.log('Request failed', error);
				});
		});

function update() {
		updateLinks();

		let nodes = svg.selectAll(".node")
				.data(data.nodes, n=>n.name);

		nodes.exit().remove()

		let nodesEnter = nodes.enter()
				.append("g")
				.attr("class", "node")
				.attr("transform", d=>`translate(${ d.x }, ${ d.y })`)
				.call(drag)

		let node = nodes.select("circle")
		let nodeEnter = nodesEnter.append("circle")

		node.merge(nodeEnter)
				.attr("r", 6)
				.attr("stroke", (d, i)=>c10(i))
				.attr("stroke-width", 2)
				.attr("fill", "#fff")
				.attr("id", (d)=>`node-${d.name}`)

		let label = nodes.select(".label")
		let labelEnter = nodesEnter.append("g")

		label.merge(labelEnter)
				.attr("class", "label")
				.attr("transform", "translate(10,2)")

		let t1 = label.select("text")
		let t1Enter = labelEnter.append("text")

		t1.merge(t1Enter)
				.text(d=>d.local_echo ? '' : d.name)
				.attr("style", "stroke:white; stroke-width:0.4em")

		let t2 = label.select("text:nth-child(2)")
		let t2Enter = labelEnter.append("text")

		t2.merge(t2Enter)
				.text(d=>d.local_echo ? '' : d.name)
}

function updateLinks() {
		let links = svg.selectAll(".link")
				.data(data.links, l=>l.id);

		links.exit().remove();

		let linksEnter = links.enter()
				.append("g")
				.lower()
				.attr("id", l=>l.id)
				.attr("class", "link")
				.on('mousedown', (d, i)=>{
						if (d3.event.button != 0) return;
						d3.event.stopPropagation();
						d3.event.preventDefault();
						selectLink(selectedLinkId === d.id ? null : d);
				})

		let line2 = links.select('line')
		let line2Enter = linksEnter.append('line')

		line2.merge(line2Enter)
				.attr("fill", "none")
				.attr("stroke", "#fff")
				.attr("stroke-opacity", 0)
				.attr("stroke-width", "8")
				.attr("x1", function(l) {
						var sourceNode = data.nodes.filter((d, i)=>(i == l.source))[0];
						d3.select(this).attr("y1", sourceNode.y);
						return sourceNode.x
				})
				.attr("x2", function(l) {
						var targetNode = data.nodes.filter((d, i)=>(i == l.target))[0];
						d3.select(this).attr("y2", targetNode.y);
						return targetNode.x
				})

		let line = links.select('line:nth-child(2)')
		let lineEnter = linksEnter.append('line')

		line.merge(lineEnter)
				.attr("fill", "none")
				.attr("stroke", "grey")
				.attr("x1", function(l) {
						var sourceNode = data.nodes.filter((d, i)=>(i == l.source))[0];
						d3.select(this).attr("y1", sourceNode.y);
						return sourceNode.x
				})
				.attr("x2", function(l) {
						var targetNode = data.nodes.filter((d, i)=>(i == l.target))[0];
						d3.select(this).attr("y2", targetNode.y);
						return targetNode.x
				})


		let label = links.select(".label")
		let labelEnter = linksEnter.append("g")

		label.merge(labelEnter)
				.attr("class", "label")
				.attr("transform", function(l) {
						var sourceNode = data.nodes.filter(function(d, i) {
								return i == l.source
						})[0];
						var targetNode = data.nodes.filter(function(d, i) {
								return i == l.target
						})[0];
						return `translate(${ (sourceNode.x + targetNode.x)/2 }, ${ 7 + (sourceNode.y + targetNode.y)/2 })`;
				})

		let t1 = label.select("text")
		let t1Enter = labelEnter.append("text")

		t1.merge(t1Enter)
				.attr("style", "stroke:white; stroke-width:0.6em")

		let t1Top = label.select("tspan")
		let t1TopEnter = t1Enter.append("tspan")

		t1Top.merge(t1TopEnter)
				.text(d => `${ Math.round(d.latency*100) / 100 }ms`)
				.attr("text-anchor", "middle")
				.attr("dominant-baseline", "middle")
				.attr("x", 0)
				.attr("dy", -13)

		let t1Bottom = t1.select("tspan:nth-child(2)")
		let t1BottomEnter = t1Enter.append("tspan")

		t1Bottom.merge(t1BottomEnter)
				.attr("text-anchor", "middle")
				.attr("dominant-baseline", "middle")
				.text(d => getPrettyBw(d.bandwidth))
				.attr("x", 0)
				.attr("dy", +13)

		let t2 = label.select("text:nth-child(2)")
		let t2Enter = labelEnter.append("text")

		t2.merge(t2Enter)

		let t2Top = t2.select("tspan")
		let t2TopEnter = t2Enter.append("tspan")

		t2Top.merge(t2TopEnter)
				.text(d => `${ Math.round(d.latency*100) / 100 }ms`)
				.attr("text-anchor", "middle")
				.attr("dominant-baseline", "middle")
				.attr("x", 0)
				.attr("dy", -13)

		let t2Bottom = t2.select("tspan:nth-child(2)")
		let t2BottomEnter = t2Enter.append("tspan")

		t2Bottom.merge(t2BottomEnter)
				.attr("text-anchor", "middle")
				.attr("dominant-baseline", "middle")
				.text(d => getPrettyBw(d.bandwidth))
				.attr("x", 0)
				.attr("dy", +13)


		selectLink(linksById[selectedLinkId]);
}

function getLinkText(d) {
		if (d.overrides) {
				let text = `${ Math.round(d.latency*100) / 100 }ms\n`
				//if (d.overrides.bandwidth) {
						text += getPrettyBw(d.bandwidth) + "\n"
				//}
				if (d.overrides.jitter) {
						text += d.jitter + "%"
				}
				return text;
		}
		else {
				return `${ Math.round(d.latency*100) / 100 }ms ${ getPrettyBw(d.bandwidth) }`
		}
}

function getPrettyBw(bw) {
		f = 10;
		if (bw > 1024*1024*1024) {
				return Math.round((f * bw) / (1024*1024*1024))/f + "Gbps";
		}
		if (bw > 1024*1024) {
				return Math.round((f * bw) / (1024*1024))/f + "Mbps";
		}
		if (bw > 1024) {
				return Math.round((f * bw) / 1024)/f + "Kbps";
		}
		return bw + "bps";
}

function mousedown() {
		const point = d3.mouse(this);

		if (d3.event.defaultPrevented) return;

		// create only with left mouse button
		if (d3.event.button != 0) return;

		// local echo
		const node = {
				local_echo: true,
				name: lastNodeId,
				x: point[0],
				y: point[1]
		};
		data.nodes.push(node);

		fetch("/server", {
				method: "POST",
				headers: { 'Content-type': 'application/json '},
				body: JSON.stringify({ x: node.x, y: node.y }),
		}).then(r=>{
				// XXX: we could grab then node ID at this point and sync incrementally
				// rather than just refresh everything
				fetchData();
		}).catch(function(error) {
				console.log('Request failed', error);
		});

		lastNodeId++;
		update();
}

function selectLink(link) {
		if (selectedLinkId !== null) {
				d3.select(`#${selectedLinkId}`)
						.attr("fill", "")
						.select('line:nth-child(2)')
						.attr("stroke", "grey")
				selectedLinkId = null;
		}

		if (!link) {
				document.getElementById("local").style.display = 'none';
				return;
		}

		selectedLinkId = link.id;

		document.getElementById("local").style.display = 'block';

		for (type of ['bandwidth', 'latency', 'jitter']) {
				document.getElementById(`link_${type}`).value = link[type];
				if (link.overrides && link.overrides[type]) {
						document.getElementById(`pin_${type}`).style.display = 'none';
						document.getElementById(`unpin_${type}`).style.display = 'inline';
				}
				else  {
						document.getElementById(`pin_${type}`).style.display = 'inline';
						document.getElementById(`unpin_${type}`).style.display = 'none';
				}
		}

		d3.select(`#${selectedLinkId}`)
				.attr("fill", "red")
				.select('line:nth-child(2)')
				.attr("stroke", "red")
}

function fetchData() {
		fetch("/data")
				.then(r=>r.json())
				.then(json=>{
						console.log(json);
						const new_data = {
								nodes: json.nodes,
								links: json.links,
						}
						for (let i in data.nodes) {
								new_data.nodes[i] = json.nodes[i] ? json.nodes[i] : data.nodes[i];
						}
						data = new_data;
						lastNodeId = data.nodes.length;

						for (let link of data.links) {
								link.id = `l_${link.source}_${link.target}`;
								linksById[link.id] = link;
						}

						update();
				})
				.catch(function(error) {
						console.log('Request failed', error);
				});
}

function fetchDefaults() {
		fetch("/defaults")
				.then(r=>r.json())
				.then(json=>{
						console.log(json);

						for (i of [
								'bandwidth',
								'max_latency',
								'min_bandwidth',
								'jitter',
								'latency_scale',
								'client_latency',
								'client_bandwidth',
								'client_jitter',
						]) {
								document.getElementById(i).value = json[i];
						}
						document.getElementById('decay_bandwidth').checked = json.decay_bandwidth;
						document.getElementById(json.cost_function).checked = true;
				})
				.catch(function(error) {
						console.log('Request failed', error);
				});
}

function applyDefaults() {
		fetch("/defaults", {
				method: "PUT",
				headers: { 'Content-type': 'application/json '},
				body: JSON.stringify({
						// we sanitise on the server
						bandwidth:       document.getElementById('bandwidth').value,
						decay_bandwidth: document.getElementById('decay_bandwidth').checked,
						min_bandwidth:   document.getElementById('min_bandwidth').value,
						max_latency:     document.getElementById('max_latency').value,
						jitter:          document.getElementById('jitter').value,
						cost_function:   document.querySelector('input[name="cost_function"]:checked').value,
						latency_scale:   document.getElementById('latency_scale').value,
						client_latency:  document.getElementById('client_latency').value,
						client_bandwidth:document.getElementById('client_bandwidth').value,
						client_jitter:   document.getElementById('client_jitter').value,
				})
		}).then(r=>{
				// grab sanitised versions from the server
				fetchDefaults();
				fetchData();
		})
		.catch(function(error) {
				console.log('Request failed', error);
		});
}

function pinOverride(type) {
		link = linksById[selectedLinkId];
		json = {}
		json[type] = document.getElementById(`link_${type}`).value;

		fetch(`/link/${link.source}/${link.target}/${type}`, {
				method: "PUT",
				headers: { 'Content-type': 'application/json '},
				body: JSON.stringify(json),
		}).then(r=>{
				fetchData();
		})
		.catch(function(error) {
				console.log('Request failed', error);
		});
}

function unpinOverride(type) {
		link = linksById[selectedLinkId];

		fetch(`/link/${link.source}/${link.target}/${type}`, {
				method: "DELETE",
		}).then(r=>{
				fetchData();
		})
		.catch(function(error) {
				console.log('Request failed', error);
		});
}

svg.on('mousedown', mousedown);

fetchData();
fetchDefaults();

function translateAlong(path, backwards) {
		var node = path.node();
		// return an interpolator factory
		return function(d, i) {
				// return the interpolator itself
				return function(t) {
						t = backwards ? (1.0 - t) : t;
						var l = node.getTotalLength();
						var p = node.getPointAtLength(t * l);
						return "translate(" + p.x + "," + p.y + ")";
				};
		};
}

function eventIdToMessageId(target, event_id) {
		event_id = event_id.replace(":", "_").replace("$", "_");
		return `m_${target}_${event_id}`
}

var exampleSocket = new WebSocket("ws://" + window.location.host + "/event_notifs");
exampleSocket.onmessage = function (event) {
		var event_data = JSON.parse(event.data);

		console.log("Received WS event", event_data);

		if (event_data.event_type == "sending") {
				// animate a message through the network path with the right timings.
				const dest = event_data.path[event_data.path.length - 1];
				message = svg.append("g")
						.attr("id", eventIdToMessageId(dest, event_data.event))
						.attr("class", "message")

				message.append("circle")
						.attr("r", 4)
						.attr("fill", c10(hashString(event_data.event)))
						// .attr("stroke", c10(hashString(event_data.event)))
						// .attr("stroke-opacity", 1)
						// .attr("fill-opacity", 0)

				// message.append("text")
				//     .attr("dx", "8px")
				//     .attr("dy", "-8px")
				//     .text(msg);

				const path = event_data.path;
				for (let i = 0; i < path.length - 1; i++) {

						let from = path[i], to = path[i+1], backwards = false;
						if (from > to) {
								from = path[i+1];
								to = path[i];
								backwards = true;
						}

						const hop = svg.select(`#l_${from}_${to}`).select("line");
						message = message.transition()
								// 2.5x is a fudge factor to slow the packets down to take delays due to HTTPS into account
								// so the correlation between a packet being sent & received is more obvious.
								.duration(hop.datum().latency * 1)
								.ease(d3.easeLinear)
								.attrTween("transform", translateAlong(hop, backwards));
				}
		}
		else if (event_data.event_type == "receive") {
				const target = parseInt(event_data.target.replace("synapse", ""));

				// we should have already seen this message received; now delete it
				svg.select('#' + eventIdToMessageId(target, event_data.event)).remove();

				const halo = svg.append("circle")
						.attr("cx", data.nodes[target].x)
						.attr("cy", data.nodes[target].y)
						.attr("fill", () => c10(hashString(event_data.event)))
						.attr("stroke", () => c10(hashString(event_data.event)))
						.attr("r", 6)
						.attr("fill-opacity", .75)
						.attr("stroke-opacity", 1)
						.transition()
						.duration(1000)
						.ease(d3.easeCubicOut)
						.attr("r", 20)
						.attr("fill-opacity", 0)
						.attr("stroke-opacity", 0)
						.remove()

				d3.selectAll(".node")
						.data(data.nodes.filter(d=>d.name==target), d=>d.name)
						.select("circle")
						.attr("stroke", () => c10(hashString(event_data.event)))
		}
}

