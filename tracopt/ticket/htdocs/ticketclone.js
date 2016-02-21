// Generated by CoffeeScript 1.10.0
(function() {
  var $, addCloneAction, addField, captionedButton, commentClone;

  $ = jQuery;

  captionedButton = function(symbol, text) {
    if (ui.use_symbols) {
      return symbol;
    } else {
      return symbol + " " + text;
    }
  };

  addField = function(form, name, value) {
    value = value != null ? $.htmlEscape(value) : '';
    return form.append($("<input type=\"hidden\" name=\"field_" + name + "\" value=\"" + value + "\">"));
  };

  addCloneAction = function(container) {
    var btns, c, cform, form, i, len, name, oldvalue, ref;
    form = $("<form action=\"" + baseurl + "/newticket\" method=\"post\">\n <div class=\"inlinebuttons\">\n  <input type=\"submit\" name=\"clone\"\n         value=\"" + (captionedButton('+', _('Clone'))) + "\"\n         title=\"" + (_("Create a new ticket from this comment")) + "\">\n  <input type=\"hidden\" name=\"__FORM_TOKEN\" value=\"" + form_token + "\">\n  <input type=\"hidden\" name=\"preview\" value=\"\">\n </div>\n</form>");
    for (name in old_values) {
      oldvalue = old_values[name];
      if (name !== "id" && name !== "summary" && name !== "description" && name !== "status" && name !== "resolution") {
        addField(form, name, oldvalue);
      }
    }
    for (i = 0, len = container.length; i < len; i++) {
      ref = container[i], btns = ref[0], c = ref[1];
      if (!btns.length) {
        return;
      }
      cform = form.clone();
      addField(cform, 'summary', _("(part of #%(ticketid)s) %(summary)s", {
        ticketid: old_values.id,
        summary: old_values.summary
      }));
      addField(cform, 'description', _("Copied from [%(source)s]:\n----\n%(description)s", {
        source: "ticket:" + old_values.id + "#comment:" + c.cnum,
        description: c.comment
      }));
      btns.prepend(cform);
    }
  };

  commentClone = function(chgs) {
    var c;
    return addCloneAction((function() {
      var i, len, results;
      results = [];
      for (i = 0, len = chgs.length; i < len; i++) {
        c = chgs[i];
        results.push([$("#trac-change-" + c.cnum + "-" + c.date + " .trac-ticket-buttons"), c]);
      }
      return results;
    })());
  };

  $(document).ready(function() {
    var c;
    if ((typeof old_values !== "undefined" && old_values !== null) && (typeof changes !== "undefined" && changes !== null)) {
      return commentClone((function() {
        var i, len, results;
        results = [];
        for (i = 0, len = changes.length; i < len; i++) {
          c = changes[i];
          if ((c.cnum != null) && c.comment && c.permanent) {
            results.push(c);
          }
        }
        return results;
      })());
    }
  });

}).call(this);
