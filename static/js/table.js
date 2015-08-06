// generic table fill code for IRRExplorer

function renderCell(data, fieldname, label) {

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
                    return "<a href=\"http://lg.ring.nlnog.net/query/" + data + "\">" + data + "</a>";
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

    for (var idx in table_keys) {
        var key = table_keys[idx];
        var table_entry = table_data[key];

        var entry_fields = Object.keys(table_entry);

        for (var efi in entry_fields) {
            field_name = entry_fields[efi];
            if (field_name == "label") {
                continue; // this is reserved for coloring of advice
            }
            if (fields.indexOf(field_name) == -1) {
                fields.push(field_name);
            }
        }
    }

    return fields;
}

function populatetable(table_name, table_data, start_fields) {

    console.log("populate table: " + table_name);
    console.log(table_data);
    console.log(start_fields);
    console.log("--");

    fields = getfields(table_data, start_fields);
    console.log(fields);

    $(table_name).hide();

    rows = [];
    table_keys = Object.keys(table_data);

    console.log(table_keys);

    for (var idx in table_keys) {
        key = table_keys[idx];

        table_entry = table_data[key];
        row = [];
        for (var f in fields) {
            field = fields[f];
            if (field == "prefix") { // hack on
                row.push('<a href="/' + start_fields[0] + '/' + key + '?exact=true">' + key + '</a>');
            }
            else if (field == start_fields[0]) {
                row.push('<a href="/' + start_fields[0] + '/' + key + '">' + key + '</a>');
            }
            else {
                row.push(renderCell(table_entry[field], field, table_entry["label"]))
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
    if ( ! $.fn.DataTable.isDataTable(table_name) ) {
        $(table_name).dataTable( {
                "data": rows,
                "columns": colsdisp,
                "searching": false,
                "lengthChange": false,
                "bPaginate": false,
                "columnDefs": [ { 'type': 'ip-address', 'targets': 0 } ]
            } );
    } else {
        // just update, already set the table up once
        $(table_name).dataTable().fnClearTable();
        $(table_name).dataTable().fnAddData(rows);

    }

    $(table_name).show();
}

