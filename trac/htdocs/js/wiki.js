(function($){

    // Provides expand/collapse button for central wiki column ($wikipage)
    // within its container ($content).

    window.wikiColumn = function($wikipage) {
      var $content = $("#content");
      $("<span id='trac-wiki-expander'></span>").on("click", function () {
        $content.toggleClass('narrow');
        if ($content.hasClass('narrow'))
          centerLargeElements();
        else
          resetLargeElements();
      }).prependTo($wikipage);

      // Auto-centering of top-level elements larger than #wikipage's max-width
      var wppl = parseInt($wikipage.css('padding-left'));
      var wppr = parseInt($wikipage.css('padding-right'));
      var wppl_ratio = wppl / (wppl + wppr);
      var wpw = $wikipage.width() - wppl;
      var large_elements = [];
      var excesses = [];
      var detectLargeElement = function() {
        var excess = $(this).width() - wpw;
        if (excess > 0) {
          large_elements.push(this);
          excesses.push(excess);
        }
        return excess;
      };
      var centerLargeElement = function(i, wpleft, excess) {
          var offset_to_the_left;
          if (excess > wppl)
              offset_to_the_left = (excess - wppl) / 2;
          else
              offset_to_the_left = excess * wppl_ratio;
          if (offset_to_the_left > wpleft)
            offset_to_the_left = wpleft;

          $(i).css({'margin-left': -offset_to_the_left,
                    'background': 'rgba(255, 255, 255, .8)'});
      };
      var centerLargeElements = function() {
        var wikipage_left = $wikipage.offset().left;
        for (var i = 0; i < large_elements.length; i++) {
          centerLargeElement(large_elements[i], wikipage_left, excesses[i]);
        }
      };
      var resetLargeElements = function() {
        for (var i = 0; i < large_elements.length; i++) {
          $(large_elements[i]).css({'margin-left': 0, 'background': 'none'});
        }
      };
      var detectLargeImage = function() {
        var excess = detectLargeElement.apply(this);
        if (excess > 0)
          centerLargeElement(this, $wikipage.offset().left, excess);
      };
      $("#wikipage > table").each(detectLargeElement);
      $("#wikipage > p > a > img").one("load", detectLargeImage).each(
        function() {
          if (this.complete)
            detectLargeImage(this);
        }
      );
      $("#wikipage > div").each(detectLargeElement);
      $(window).resize(centerLargeElements);
      centerLargeElements();
  };


  jQuery(document).ready(function($) {
    $("#content").find("h1,h2,h3,h4,h5,h6").addAnchor(_("Link to this section"));
    $("#content").find(".wikianchor").each(function() {
      $(this).addAnchor(babel.format(_("Link to #%(id)s"), {id: $(this).attr('id')}));
    });
    $(".foldable").enableFolding(true, true);
  });

})(jQuery);
