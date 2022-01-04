$(document).ready(function() {
	
	var pcr = 2   // per character rate
	var pwr = 9  // per word rate
	var pqr = 100 // per question rate
	
	$("#text_holder").hide();

	// [START gae_flex_websockets_js]

	/* If the main page is served via https, the WebSocket must be served via "wss" (WebSocket Secure) */
	var scheme = window.location.protocol == "https:" ? 'wss://' : 'ws://';
	var webSocketUri =  scheme
				  + window.location.hostname
				  + (location.port ? ':'+location.port: '')
				  + '/chat';
	/* Get elements from the page */
	/* Establish the WebSocket connection and register event handlers. */
	var websocket = new WebSocket(webSocketUri);
	
	
	
	

	var check_timer = setInterval(function() {

		var p = {
		"type": "check"
		};
		var packet = JSON.stringify(p); 
		websocket.send(packet); 
		}, 6000);	  






	websocket.onopen = function() {  // send the joined user info to the server
		var p = {
		"type": "joined",
		"username": "{{session['username']}}"
		};
		var packet = JSON.stringify(p);
		websocket.send(packet)
	};





	websocket.onclose = function() {  // send the logged off user info to the server
		var p = {
		"type": "left",
		"username": "{{session['username']}}"
		};
		var packet = JSON.stringify(p);
		websocket.send(packet)
	};





// --------------- WEBSOCKET ON MESSAGE ---------------------------

	websocket.onmessage = function(packet) {

		var pd = packet.data
		var p = JSON.parse(pd)

		if (p.type == "result") {   // update the delivery div based on the date and time
			if (p.delivery == "monday_by_11") {
				$('#delivery').html("<b> Translation will be delivered by Monday at 11am</b>");
			} 
			if (p.delivery == "tonight_by_23") {
			$('#delivery').html("<b> Translation will be delivered by tonight at 23:00</b>");
			}
			if (p.delivery == "tomorrow_by_11") {
			$('#delivery').html("<b> Translation will be delivered by tomorrow at 11am</b>");
			}
			if (p.delivery == "today_by_11") {
			$('#delivery').html("<b> Translation will be delivered by today at 11am</b>");
			}
			if (p.delivery == "today_by_17") {
			$('#delivery').html("<b> Translation will be delivered by today at 17:00</b>");
			}
			if (p.delivery == "now") {
			$('#delivery').html("<b> Translation will be delivered within 30 minutes</b>");
			}
		}



		// MK INCOMING -- OUTGOING AREA -------------------------------------------------------


		if (p.type == "question_relay") {  // relay message to MK

			var this_rand = Math.floor((Math.random() * 1000) + 1);

			var incoming_div = '<div name="' + this_rand + '"></div>'
			var incoming_div_ref = 'div[name=' + this_rand + ']'

			var timer_div = '<div name="' + this_rand + '_timer"></div>'
			var timer_div_ref = 'div[name=' + this_rand + '_timer]'

			$('div[name=archive_incoming]').append(incoming_div)
			$('div[name=archive_incoming]').append(timer_div)

			$(incoming_div_ref).html("<br>" + p.question + "<p>" + p.subtype + "<input type = 'text' name='" + this_rand + "' /><button id='" + this_rand + "'>Reply</button>");

			$(timer_div_ref).html(p.delivery)

			var button_ref = '#' + this_rand
			var field_ref = 'input[name=' + this_rand + ']'

			$(button_ref).unbind().click(function() {

				var raw_response = $(field_ref).val();
				var response = "<b>Reply: </b><p>" + raw_response
 
				var question = p.subtype + ": " + p.question

				var p2 = {
					"type": "archive",
					"username": p.asker,
					"question": question,
					"response": response
				};
				var packet2 = JSON.stringify(p2);
				websocket.send(packet2)
				$(incoming_div_ref).append("<b>Answered!");
			});
		}
		// END MK INCOMING -- OUTGOING -----------------------------------------------------------	

		if (p.type == "update_yr_outgoing") {
			$('#answer').html("Answer Arrived")
		}
			

		$(".ask").unbind().click(function(){

			var type = this.name
			var letters = /[A-Za-z0-9_!?,.';]+$/;
			var symbols = /[^A-Za-z0-9_!?,.';]+$/;

			var current_balance = $('#balance').text();

			if (type == "English_correction") {                         // if its an English correction
				if ($("#txt").val().match(letters)) {                   // which contains some alpahabet letters,
					var words = $("#txt").val().split(" ").length       // then we split the string by spaces and count the words
					var cost = words * pwr
		
					if (cost > current_balance) {
						$('div[name=question_confirmation]').html("<p>The cost of this English check request would be " + cost + ", but your current balance is " + current_balance + ".  Please re-charge your account.");
					} 
					else {
		
						$('div[name=question_confirmation]').html("<p>This is an English check request which contains " + words + " words.  The per word rate is " + pwr + " yen, so it will cost " + cost + " yen.  Continue?<p><button id = 'continue'>Continue</button><button id = 'quit'>Quit</button>");
						$('#txt').attr("disabled", true);
			
						var contents = $("#txt").val()
						contents = type + "|||||||" + contents
						$("#text_holder").val(contents)

						}
					}	
				else { 
				$('div[name=question_confirmation]').html("You can only put English characters into an English correction request.");
				}
			}

			if (type == "Translation") {							// if its a translation request
				if ($("#txt").val().match(symbols)) {				// which contains some Japanese characters,
					var characters = $("#txt").val().length;		// then we count the characters
					var cost = characters * pcr
		
					if (cost > current_balance) {
						$('div[name=question_confirmation]').html("<p>The cost of this translation request would be " + cost + ", but your current balance is " + current_balance + ".  Please re-charge your account.");
					} 
					else {
			
						$('div[name=question_confirmation]').html("<p>This is a translation request which contains " + characters + " characters.  The per character rate is " + pcr + " yen, so it will cost " + cost + " yen. Continue?<p><button id = 'continue'>Continue</button><button id = 'quit'>Quit</button>");
						$('#txt').attr("disabled", true);
			
						var contents = $("#txt").val()
						contents = type + "|||||||" + contents
						$("#text_holder").val(contents)
			
						}
					}
				else {
					$('div[name=question_confirmation]').html("You can only put Japanese characters into a translation request.");
				}
			}

			if (type == "Question") {							// if its a question, we just charge a flat rate
				var characters = $("#txt").val().length;        // However, there is a character limit, which we have to check before proceeding
				if (characters < 300) {
					var cost = pqr
		
					if (cost > current_balance) {
						$('div[name=question_confirmation]').html("<p>The cost of this question would be " + cost + ", but your current balance is " + current_balance + ".  Please re-charge your account.");
					} 
					else {
			
						$('div[name=question_confirmation]').html("<p>The per question rate is " + pqr + " yen, so it will cost " + cost + " yen. Continue?<p><button id = 'continue'>Continue</button><button id = 'quit'>Quit</button>");
						$('#txt').attr("disabled", true);
						
						var contents = $("#txt").val()
						contents = type + "|||||||" + contents
						$("#text_holder").val(contents)
			
						}
					}
				else {
				$('div[name=question_confirmation]').html("The maximum number of characters for a question is 300.  Please reduce the number of characters in this question.");
				}
			}
		});
		
		
		
		

		$("#continue").unbind().click(function() {

			var currentdate = new Date(); 
			var hour = currentdate.getHours();
			var minute = currentdate.getMinutes();
			
			var delivery_schedule = "Submitted at " + String(hour) + ":" + String(minute)

			var contents = $("#text_holder").val();
			var parts = contents.split("|||||||")
			var sub_type = parts[0]
			contents = parts[1]

			// --------- re-calculate the cost and times based on the type of question (pulled from the question itself after splitting it up -----
			if (sub_type == "English_correction") {
				var words = $("#txt").val().split(" ").length;
				var cost = words * pwr
			}
			if (sub_type == "Translation") {
				var characters = $("#txt").val().length;
				var cost = characters * pcr
			}
			if (sub_type == "Question") {
				var cost = pqr
			}
			// ----------------------------------------------------------------------
			var p = {
				"type": "question",
				"data": contents,
				"subtype": sub_type,
				"delivery": delivery_schedule,
				"username": "{{session['username']}}",
				"cost": cost,
				};
			var packet = JSON.stringify(p);
			websocket.send(packet)

			$('div[name=question_confirmation]').html("<p>Your question has been sent, and your balance has been updated.<p><button id = 'continue'>Continue</button>");
		
			var old_balance = $('#balance').text();
			var new_balance = parseFloat(old_balance) - cost
			$('#balance').html(new_balance);
			$('#txt').attr("disabled", false);
			$('#txt').val("--")
		});
		
	}
// ---------------- END OF ON MESSAGE BLOCK -----------------------------




	$('#backlog_check').unbind().click(function () {
		var p = {
			"type": "backlog_check"
		};
		var packet = JSON.stringify(p); 
		websocket.send(packet);
	});





	$('#quit').unbind().click(function () {

		$('div[name=question_confirmation]').html("");
		$('#txt').attr("disabled", false);

	});








	$('#email').unbind().click( function() {
		var contents = $('#email_box').val();
		var p = {
			"type": "email",
			"username": "{{session['username']}}",
			"contents": contents
		}
		var packet = JSON.stringify(p);
		websocket.send(packet)
		$('div[name=email_area]').html("Your email has been sent.  We will respond as soon as possible.")
	});






	$('#logout').click( function () {
		var p = {
			"type": "left",
			"username": "{{session['username']}}"
		};
		var packet = JSON.stringify(p);
		websocket.send(packet);
		location.href = "{{ url_for('index')}}";
	});



	websocket.onerror = function(e) {
		log('Error (see console)');
		console.log(e);
  };

});
// [END gae_flex_websockets_js]