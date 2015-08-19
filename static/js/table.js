// generic table fill code for IRRExplorer

function state_loaded() {
    $("#btnsearch").prop("disabled",false);
    $("#loading").hide();
    $("#btnsearch").html('Search');
}

function state_loading() {
    $("#btnsearch").prop("disabled",true);
    $("#btnsearch").html('Searching...');
    $("#loading").show();
}

// TODO: switch fieldname and data as I find the order rather confusing (htj)
function renderCell(data, fieldname, label) {

    console.log("renderCell: " + data + " " + fieldname + " " + label);
    if (typeof data != 'undefined') {
        switch (data.toString()) {
            case "true":
                return "<img alt='T' title='True' src='/static/img/true.png'>";
            case "false":
                return "<img alt='F' title='False' src='/static/img/false.png'>";
            default:
                if (fieldname == "advice") {
                    console.log(label);
                    return "<span class='label label-" + label + "'>" + data + "</span>";
                } else if (fieldname == "bgp") {
                    return "<a href=\"http://lg.ring.nlnog.net/query/" + label + "\">" + data + "</a>";
                } else if (fieldname == "path") {
                    return data.join(" &#10132 ");
                } else if (fieldname == "members") {
                    return data.join(", ");
                }
                else {
                    return data;
                }
        }
    } else {
        return "";
    }
}


function getfields(table_data, start_fields) {

    var table_keys = Object.keys(table_data);

    var fields = start_fields.slice(0); // clone

    var last_fields = [];

    for (var idx in table_keys) {
        var key = table_keys[idx];
        var table_entry = table_data[key];

        var entry_fields = Object.keys(table_entry);

        for (var efi in entry_fields) {
            field_name = entry_fields[efi];
            if (field_name == "label") {
                continue; // this is reserved for coloring of advice
            }
            if (field_name == "advice") {
                if (last_fields.indexOf(field_name) == -1) {
                    last_fields.push(field_name);
                }
                continue;
            }
            if (fields.indexOf(field_name) == -1) {
                fields.push(field_name);
            }
        }
    }
    fields = fields.concat(last_fields);

    return fields;
}

function populatetable(table_name, table_data, start_fields) {

    console.log("populate table: " + table_name);
    console.log(table_data);
    console.log(start_fields);
    console.log("--");

    fields = getfields(table_data, start_fields);
    console.log("fields: " + fields);

    $(table_name).hide();

    rows = [];
    table_keys = Object.keys(table_data);

    console.log(table_keys);

    for (var idx in table_keys) {
        key = table_keys[idx];
        console.log(key);

        table_entry = table_data[key];
        console.log(table_entry);

        if($.isArray(table_data)) {
            // useless index, change to first
            console.log(table_entry);
            key = table_entry[start_fields[0]];
            console.log(key);
        }

        row = [];
        for (var f in fields) {
            field = fields[f];
            if (field == start_fields[0]) {
                row.push('<a href="/search/' + key + '">' + key + '</a>');
            }
            else {
                var label;
                if (field == "bgp") {
                    label = key;
                }
                else if (field == "advice") {
                    label = table_entry["label"];
                }
                row.push(renderCell(table_entry[field], field, label));
            }
        }
        rows.push(row);
    };

    colsdisp = [];
    for (var f in fields) {
        field = fields[f];
        coldisp = {"title": field}
        colsdisp.push(coldisp);
    }
    // TODO: don't do the columnDefs if first row is not a prefix...
    if ( ! $.fn.DataTable.isDataTable(table_name) ) {
        var table= {
            "data": rows,
            "columns": colsdisp,
            "searching": false,
            "lengthChange": false,
            "bPaginate": false
        };
        if (start_fields[0] == "prefix") {
            table["columnDefs"] = [ { 'type': 'ip-address', 'targets': 0 } ];
        }
        if (start_fields[1] == "depth") { // order by depth if it exists (as macro expansion)
            table["order"] = [[ 1, "asc" ]]
        }
        $(table_name).dataTable(table);
    } else {
        // just update, already set the table up once
        $(table_name).dataTable().fnClearTable();
        $(table_name).dataTable().fnAddData(rows);

    }

    $(table_name).show();
}

