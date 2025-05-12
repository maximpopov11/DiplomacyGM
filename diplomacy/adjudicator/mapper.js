// if you make any rendering changes,
// make sure to sync them with mapper.js


// Python interoperablity
const True = true;
const False = false;
const None = undefined;

// dict with name: primary_loc
// fed in by mapper.py
const location_data = %s;
const svg_config = %s;

const coast_to_province = %s;
const province_to_unit_type = %s;
const province_to_province_type = %s;

const arrow_layer = document.getElementById(svg_config["arrow_output"]);

unit_elements = {};

// Function to be called with next argument if next is leftclick
let left_callback = leftclick;

// Either "province" or "unit". If "unit", then clicking on a province without a unit will reset it
let left_callback_type = "unit";

let right_callback = rightclick;

let right_callback_type = "unit";

let order_array = {};

let immediate = %s;

function obj_clicked(event, name, isUnit) {
    event.preventDefault();
    let callback;
    let callback_type;
    if (event.button == 0) {
        // Left click
        callback = left_callback
        callback_type = left_callback_type;
    } else if (event.button == 2) {
        // Right click
        callback = right_callback;
        callback_type = right_callback_type;
    } else {
        console.log("Unknown button type!");
        return;
    }
    if (callback_type == "unit") {
        if (province_to_unit_type[name] === undefined) {
            return;
        }
    }
    callback(name);
    rerender_text();
}

function make_elem(name, dict) {
    e = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(dict)) {
        e.setAttribute(key, value);
    }
    return e;
}

function rerender_text() {
    let textbox = document.getElementById("order_output_textbox");
    let box = textbox.children[0];
    textbox.innerHTML = '';
    textbox.append(box);

    for (const [origin, order] of Object.entries(order_array)) {
        let line = "";
        switch (order.type) {
            case "Hold":
                line = `${order.origin} Holds`;
                break;
            case "Core":
                line = `${order.origin} Cores`;
                break;
            case "Move":
                line = `${order.origin} -> ${order.destination}`;
                break;
            case "Convoy":
                line = `${order.origin} Convoys ${order.support} -> ${order.destination}`;
                break;
            case "Support":
                if (order.support != order.destination) {
                    line = `${order.origin} Supports ${order.support} -> ${order.destination}`;
                } else {
                    line = `${order.origin} Supports ${order.support} Hold`;
                }
                break;
            default:
                console.log("Unknown order!");
        }
        elem = make_elem("tspan", {
            x: box.getAttribute("x"),
            dy: "1.2em",
        });
        elem.innerHTML = line + '\n';
        textbox.append(elem);

    }
}

function reset_state() {
    left_callback = leftclick;
    right_callback = rightclick;
    left_callback_type = "unit";
    right_callback_type = "unit";
}

function pull_coordinate(anchor, coordinate, pull=undefined, limit=0.25) {
    if (pull === undefined) {
        pull = 1.5 * svg_config["unit_radius"];
    }

    ax = anchor[0];
    ay = anchor[1];
    cx = coordinate[0];
    cy = coordinate[1];
    dx = ax - cx;
    dy = ay - cy;

    distance = (dx**2 + dy**2) ** 0.5;
    if (distance == 0) {
        return coordinate;
    }

    // if the area is small, the pull can become too large of the percent of the total arrow length
    pull = Math.min(pull, distance * limit);

    scale = pull / distance;
    return [cx + dx * scale, cy + dy * scale];
}

function draw_order(order, elems) {
    if (order["origin"] in unit_elements) {
        for (obj of unit_elements[order["origin"]]) {
            obj.remove();
        }
    }
    unit_elements[order["origin"]] = [];
    unit_elements[order["origin"]] = elems;
    for (e of elems) {
        console.log(e);
        arrow_layer.append(e);
    }
}

function draw_hold(order) {
    const coord = location_data[order["origin"]];
    draw_order(order, [make_elem("circle", 
        {
            cx: coord[0],
            cy: coord[1],
            r: svg_config["unit_radius"],
            fill: "none",
            stroke: "black",
            "stroke-width": svg_config["order_stroke_width"],
            "shape-rendering": "geometricPrecision"
        }
    )])
}

for (entry of immediate) {
    draw_hold({
        type: "Hold",
        origin: entry,
    });
}

function draw_core(order) {
    const coord = location_data[order["origin"]];
    draw_order(order, [make_elem("rect", 
        {
            x: coord[0] - svg_config["unit_radius"],
            y: coord[1] - svg_config["unit_radius"],
            width: svg_config["unit_radius"] * 2,
            height: svg_config["unit_radius"] * 2,
            fill: "none",
            stroke: "black",
            "stroke-width": svg_config["order_stroke_width"],
            transform: `rotate(45 ${coord[0]} ${coord[1]})`,
            "shape-rendering": "geometricPrecision"

        }
    )])
}

function draw_move(order) {
    let startcoord = location_data[order["origin"]];
    let endcoord = location_data[order["destination"]];
    if (province_to_unit_type[order["destination"]] !== undefined) {
        endcoord = pull_coordinate(startcoord, endcoord);
    }
    draw_order(order, [make_elem("path",
        {
            d: `M ${startcoord[0]} ${startcoord[1]} L ${endcoord[0]} ${endcoord[1]}`,
            fill: "none",
            stroke: "black",
            "stroke-width": svg_config["order_stroke_width"],
            "stroke-linecap": "round",
            "marker-end": `url(#arrow)`,
            "shape-rendering": "geometricPrecision"
        }
    )])
}

function draw_convoy(order) {
    const coord = location_data[order["origin"]];
    draw_order(order, [make_elem("circle", 
        {
            cx: coord[0],
            cy: coord[1],
            r: svg_config["unit_radius"] / 2,
            fill: "none",
            stroke: "black",
            "stroke-width": svg_config["order_stroke_width"] * 2 / 3,
            "shape-rendering": "geometricPrecision"
        }
    )])
}

function draw_support(order) {
    let startcoord = location_data[order["origin"]];
    let supportcoord = location_data[order["support"]];
    let endcoord = location_data[order["destination"]];
    let trueendcoord = endcoord;
    const dasharray_size = 2.5 * svg_config["order_stroke_width"];
    let marker_end = "arrow";
    let marker_start = ""
    if (supportcoord == endcoord) {
        marker_end = "ball";
        if (order["destination"] in order_array) {
            let other = order_array[order["destination"]];
            if (other["destination"] == order["origin"] && other["support"] == order["origin"] && !("sync" in other)) {
                // Double support-hold situation
                // We swap so our start is on their end
                // That way the dashes line up
                order["sync"] = true;
                marker_start = "ball";
                marker_end = "";
                endcoord = startcoord;
                startcoord = supportcoord;
                supportcoord = endcoord;

            }
        }
    }
    if (province_to_unit_type[order["destination"]] !== undefined) {
        if (supportcoord == endcoord) {
            endcoord = pull_coordinate(startcoord, endcoord, svg_config["unit_radius"]);
            supportcoord = endcoord
        } else {
            endcoord = pull_coordinate(supportcoord, endcoord);
        }
    }
    
    startcoord = pull_coordinate(supportcoord, startcoord, svg_config["unit_radius"]);

    path = [make_elem("path",
        {
            "d": `M ${startcoord[0]},${startcoord[1]} Q ${supportcoord[0]},${supportcoord[1]} ${endcoord[0]},${endcoord[1]}`,
            "fill": "none",
            "stroke": "black",
            "stroke-dasharray": `${dasharray_size} ${dasharray_size}`,
            "stroke-width": svg_config["order_stroke_width"],
            "stroke-linecap": "round",
            "marker-start": `url(#${marker_start})`,
            "marker-end": `url(#${marker_end})`,
            "shape-rendering": "crispEdges",
            "shape-rendering": "geometricPrecision",
            "overflow": "visible"
        }
    )]
    if (supportcoord == endcoord) {
        path.push(make_elem("circle", 
            {
                cx: trueendcoord[0],
                cy: trueendcoord[1],
                r: svg_config["unit_radius"],
                fill: "none",
                stroke: "black",
                "stroke-linecap": "round",
                "stroke-width": svg_config["order_stroke_width"],
                "shape-rendering": "geometricPrecision",
                "stroke-dasharray": `${dasharray_size * 2 / 3} ${dasharray_size * 2 / 3}`
            }
        ))
    }
    draw_order(order, path);
}

function leftclick(porigin) {
    // Move
    left_callback_type = "province";
    // Support
    right_callback_type = "unit";

    left_callback = (pdestination) => {
        // Clicking on a coast indicator with a army should send you to the province
        if (province_to_unit_type[pdestination] == "a") {
            if (pdestination in coast_to_province) {
                pdestination = pdestination[coast_to_province]
            }
        }
        order_array[porigin] = {
            type: "Move",
            origin: porigin,
            destination: pdestination,
        };
        draw_move(order_array[porigin]);
        reset_state();
    }
    right_callback = (psupport) => {
        left_callback_type = "province";

        left_callback = (pdestination) => {
            // Clicking on a coast indicator with a army should send you to the province
            if (province_to_unit_type[psupport] == "a") {
                if (psupport in coast_to_province) {
                    psupport = psupport[coast_to_province]
                }
            }
            order_array[porigin] = {
                type: "Support",
                origin: porigin,
                support: psupport,
                destination: pdestination
            };
            draw_support(order_array[porigin]);
            reset_state();
        }
        right_callback_type = left_callback_type;
        right_callback = left_callback;
    }
}

function rightclick(porigin) {
    
    if (porigin in order_array) {
        // Reset
        if (order_array[porigin]["type"] == "Core" || order_array[porigin]["type"] == "Convoy") {
            order_array[porigin] = {
                type: "Hold",
                origin: porigin
            };
            draw_hold(order_array[porigin]);
            reset_state();
            return;
        }
    }
    if (province_to_province_type[porigin] == "sea") {
        // convoy
        function convoy_callback1(psupport) {
            function convoy_callback2(pdestination) {
                // a convoy also sets the convoy'd order
                order_array[psupport] = {
                    type: "Move",
                    origin: psupport,
                    destination: pdestination,
                }
                draw_move(order_array[psupport]);
                order_array[porigin] = {
                    type: "Convoy",
                    origin: porigin,
                    support: psupport,
                    destination: pdestination,
                };
                draw_convoy(order_array[porigin]);
                reset_state();
            }
            left_callback_type = "province";
            right_callback_type = "province";
            left_callback = convoy_callback2;
            right_callback = convoy_callback2;
        }
        // Doesn't matter
        left_callback_type = "unit";
        right_callback_type = "unit";
        left_callback = convoy_callback1;
        right_callback = convoy_callback1;
    } else {
        order_array[porigin] = {
            type: "Core",
            origin: porigin
        };
        draw_core(order_array[porigin]);
        reset_state();
    }
}