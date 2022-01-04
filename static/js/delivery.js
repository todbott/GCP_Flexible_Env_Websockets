$(document).ready(function() {
  
  var currentdate = new Date(); 
  var hour = currentdate.getHours();
  
  if (22 > hour > 16) {
  	 $('#delivery').html("Translation will be delivered tonight by 23:00 JST");
	 }
  if (22 < hour <= 24) {
     $('#delivery').html("Translation will be delivered tomorrow by 11:00 JST<br><i>(Monday by 11:00 if today is Friday, Saturday or Sunday)</i>");
	 }
  if (hour < 9) {
     $('#delivery').html("Translation will be delivered today by 11:00 JST");
	 }
  if (8 < hour < 16) {
  	 $('#delivery').html("Translation will be delivered within 2 hours of request (JST)");
	 }
});