django.jQuery(document).ready(function($) {
	$('input.event-exceptions ~ ul li').delegate('a', 'click', function() {
		var exception_input = $(this).closest('ul').prev('input');
		var exception_value = $(this).prev().text();
		if($(this).attr('class') == 'clear-exceptions') {
			// [Clear all] has been clicked
			exception_input.val('{}');
			$(this).closest('ul').html('<li>None</li>');
		} else {
			// If this is the last exception, clear the list
			if($(this).closest('ul').children('li').length <= 1)
				$(this).closest('ul').html('<li>None</li>');
			else
				$(this).closest('li').remove();	
			// Remove the exception from the hidden input. Technically, it
			// would be better to JSON parse the input and dynamically
			// generate the exception list, then modify the JSON and write it
			// into the input, but there's no time.
			var exception_regex = RegExp('\\s*,?\\s*"'+exception_value+'"\\s*:\\s*\\w+\\s*', 'g');
			exception_input.val(exception_input.val().replace(exception_regex, ''));
		}
		return false;
	})
});