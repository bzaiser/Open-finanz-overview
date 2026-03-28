(function($) {
    'use strict';
    $(document).ready(function() {
        // Find all inline groups (tabular inlines in Django Admin)
        $('.inline-group').each(function() {
            var $group = $(this);
            var $header = $group.find('h2');
            
            if ($header.length) {
                // Add a toggle link to the header
                var $toggle = $('<a href="#" class="inline-toggle" style="float: right; font-size: 0.8em; margin-left: 10px;">[Ausblenden]</a>');
                $header.append($toggle);
                
                // Content to collapse (the table/grid)
                var $content = $group.find('.tabular, .stacked');
                
                $toggle.click(function(e) {
                    e.preventDefault();
                    if ($content.is(':visible')) {
                        $content.slideUp();
                        $(this).text('[Einblenden]');
                    } else {
                        $content.slideDown();
                        $(this).text('[Ausblenden]');
                    }
                });
                
                // Optional: Start collapsed for everything except the first one?
                // Let's keep them open by default as requested "ein- und ausklappbar"
            }
        });
    });
})(django.jQuery);
