$(document).ready(function () {
  function fetchResults(query) {
    $.get(`/search?text=${encodeURIComponent(query)}`, function (data) {
      const table = $('#resultsTable').DataTable();
      table.clear();
      data.forEach(row => {
        const audioHtml = `<audio controls preload="metadata" style="height:20px; width:120px;">
                             <source src="/audio/${row.id}" type="audio/mpeg"></audio>`;
        table.row.add([
          row.id, row.channel, row.video_id, row.speaker,
          row.start_time, row.end_time, row.upload_date,
          row.text, row.pos_tags, audioHtml
        ]);
      });
      table.draw();
    });
  }

  $('#resultsTable').DataTable();
  $('#searchBox').on('input', function () {
    const query = $(this).val();
    fetchResults(query);
  });

  // Initial empty fetch
  fetchResults('');
});

