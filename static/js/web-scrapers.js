$(document).ready(function() {
    $('#scrapersTable').DataTable({
        "columnDefs": [{"targets": 'no-sort',"orderable": false}],
        "ordering": false,
        "paging": false,
        "searching": false,
        "info": false
    });
    
    getScrapersData();
    
    $("#btnScraperAdd").on('click', function(){
        addScraper();
    });

    $("#btnTableUpdate").on('click', function(){
        updateScrapersTable();
    });
});

function isNumber(evt) {
    evt = (evt) ? evt : window.event;
    var charCode = (evt.which) ? evt.which : evt.keyCode;
    if ( (charCode > 31 && charCode < 48) || charCode > 57) {
        return false;
    }
    return true;
};

function getScrapersData(){
    let urlBase = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port + '/';
    let query = {
        coin: "ALL"
    };

    $.ajax({
        url: urlBase + "scraper-data?q=" + JSON.stringify(query),
        beforeSend: function(){
            console.log("Request url:", urlBase + "scraper-data?q=" + JSON.stringify(query));
        },
        success: function(result){
            let data = result.data;
            if (data.length > 0){
                for (i in data){
                    addRowScrapersTable(data[i]);
                }
            }
        },
        timeout: 60000
    });
};

function addScraper(){
    let currency = $("#InputCurrency").val();
    let frequency = $("#InputFrequency").val();

    if (currency != ""){
        let urlBase = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port + '/';
        let query = {
            coin: currency,
            frequency: parseInt(frequency)
        };

        $.ajax({
            url: urlBase + "scraper-add?q=" + JSON.stringify(query),
            beforeSend: function(){
                console.log("Request url:", urlBase + "scraper-data?q=" + JSON.stringify(query));
            },
            success: function(result){
                console.log(result.mssg);
                if (result.cod == 200){
                    let data = result.data;
                    addRowScrapersTable(data);
                }

                updateScrapersTable();
            },
            timeout: 60000
        });
    }
};

function removeScraper(coin){
    let urlBase = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port + '/';
    let query = {
        coin: coin
    };
    
    $.ajax({
        url: urlBase + "scraper-remove?q=" + JSON.stringify(query),
        async: false,
        beforeSend: function(){
            console.log("Request url:", urlBase + "scraper-remove?q=" + JSON.stringify(query));
        },
        success: function(result){
            console.log(result.mssg);
            removeRowScrapersTable(coin);

            updateScrapersTable();
        },
        timeout: 60000
    });
};

function addRowScrapersTable(data){
    let scrapersTable = $('#scrapersTable').DataTable();
    let row = scrapersTable
        .row.add([
            data.id,
            data.coin,
            data.price,
            data.lastUpdate,
            `<input id="fq-${data.coin}" class="form-control border-0" type="number" min="1" max="30" step="1" onkeypress="return isNumber(event)" value="${data.frequency}" style="width:70px;font-size:11px;">`,
            data.start,
            `<button class="btn btn-secondary" style="width:45px;font-size:11px;" type="button" data-coin="${data.coin}">` +
            `<i class="fa fa-refresh"></i>` +
            `</button> ` +
            `<button class="btn btn-secondary" style="width:45px;font-size:11px;" type="button" data-coin="${data.coin}">` +
            `<i class="fa fa-trash-o"></i>` +
            `</button>`
        ])
        .draw()
        .node();
    $( row.childNodes[0] ).addClass('align-middle text-center');
    $( row.childNodes[1] ).addClass('align-middle text-center');
    $( row.childNodes[2] ).addClass('align-middle text-center');
    $( row.childNodes[3] ).addClass('align-middle text-center');
    $( row.childNodes[4] ).addClass('align-middle text-center');
    $( row.childNodes[5] ).addClass('align-middle text-center');
    $( row.childNodes[6] ).addClass('align-middle text-center');
    $( row.childNodes[6].childNodes[0] ).on('click', function(){
        updateScraperFrequency($(this).data("coin"), $(`#fq-${$(this).data("coin")}`).val());
    });

    $( row.childNodes[6].childNodes[2] ).on('click', function(){
        removeScraper($(this).data("coin"))
    });
};

function removeRowScrapersTable(coin){
    let scrapersTable = $('#scrapersTable').DataTable();
    let indexes = scrapersTable
        .rows()
        .indexes()
        .filter( function ( value, index ) {
            return coin === scrapersTable.row(value).data()[1];
        });
    
    scrapersTable.rows(indexes).remove().draw();
};

function updateScrapersTable(){
    let scrapersTable = $('#scrapersTable').DataTable();
    let i = 0;
    let tFrequency = 0;
    scrapersTable.rows("tbody tr").every( function ( rowIdx, tableLoop, rowLoop ) {
        let scraperData = this.data();
        let urlBase = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port + '/';
        let query = {
            coin: scraperData[1]
        };

        $.ajax({
            url: urlBase + "scraper-data?q=" + JSON.stringify(query),
            async: false,
            beforeSend: function(){
                console.log("Request url:", urlBase + "scraper-data?q=" + JSON.stringify(query));
            },
            success: function(result){
                let data = result.data;
                if (data.length > 0){
                    i++;
                    scrapersTable.cell(rowIdx,2).data(data[0].price);
                    scrapersTable.cell(rowIdx,3).data(data[0].lastUpdate);
                    scrapersTable.cell(rowIdx,4).data(`<input id="fq-${data[0].coin}" class="form-control border-0" type="number" min="1" max="30" step="1" onkeypress="return isNumber(event)" value="${data[0].frequency}" style="width:70px;font-size:11px;">`);
                    tFrequency += data[0].frequency;
                }
                scrapersTable.draw();
            },
            timeout: 60000
        });
    });

    if (i > 0){
        $("#fq-avg").text(tFrequency/i);
    }else{
        $("#fq-avg").text(0);
    }
};

function updateScraperFrequency(coin, frequency){
    let urlBase = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port + '/';
    let query = {
        coin: coin,
        frequency: parseInt(frequency)
    };
    $.ajax({
        url: urlBase + "scraper-update?q=" + JSON.stringify(query),
        beforeSend: function(){
            console.log("Request url:", urlBase + "scraper-update?q=" + JSON.stringify(query));
        },
        success: function(result){
            console.log(result.mssg);

            updateScrapersTable();
        },
        timeout: 60000
    });
};
