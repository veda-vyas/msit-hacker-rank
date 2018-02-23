import csv

cspp_grades = {}
exam_activity_scores = {}
email_mentors_map = {}
rollno_email_map = {}
point_shapes = {" Rajesh. K": "star", " Neeraj Sharma": "circle", " Deepak Kumar": "square", " Manasa. A": "triangle", " Murthy Vemuri":"diamond", " Raja Babu. L":"polygon"}
point_colors = {" F":'rgb(219, 68, 55)'," B":'green'," B+":'green'," C":'orange'}

with open('rollno_email_map.csv') as f:
	csvreader2 = csv.reader(f,delimiter=',')
	for i in csvreader2:
		if i[3] not in email_mentors_map:
			email_mentors_map[i[3]] = i[2]
		if i[0] not in rollno_email_map:
			rollno_email_map[i[0]] = i[3]

feedbacks = {}

with open("feedbacks.csv") as feedbackfile:
	feedback = csv.reader(feedbackfile,delimiter=",")
	lineno = 0
	for line in feedback:
		if lineno != 0:
			feedbacks[rollno_email_map[line[1]]] = line
		lineno += 1

# print feedbacks

with open("cspp_grades.csv") as csvfile:
	csvreader = csv.reader(csvfile, delimiter=",")
	for i in csvreader:
		mentor_name = email_mentors_map[i[0]]
		if i[1] in point_colors:
			if mentor_name in point_shapes:
				point = 'CSPP-1 Grade: '+i[1]+'\nMentor: '+mentor_name+'\n\n|point { size: 7; shape-type: circle; fill-color: '+point_colors[i[1]]+'; }'
			else:
				point = 'CSPP-1 Grade: '+i[1]+'\nMentor: Rehana\n\n|point { size: 7; shape-type: circle; shape-rotation:180; fill-color: '+point_colors[i[1]]+'; }'
		else:
			if mentor_name in point_shapes:
				point = 'CSPP-1 Grade: '+i[1]+'\nMentor: '+mentor_name+'\n\n|point { size: 7; shape-type: circle; fill-color: rgb(66, 133, 244); }'
			else:
				point = 'CSPP-1 Grade: '+i[1]+'\nMentor: Rehana\n\n|point { size: 7; shape-type: circle; shape-rotation:180; fill-color: rgb(66, 133, 244); }'

		cspp_grades[i[0][1:]] = point


with open("combinedscores.csv") as csvfile2:
	csvreader2 = csv.reader(csvfile2, delimiter=",")
	for j in csvreader2:
		exam_activity_scores[j[0]] = [j[1],j[2]]

feedback_headings = ["Timestamp", "Roll Number", "Attendance", "Focus", "Seeks Help", "Actively participates in classroom discussions", "Problem-solving practice", "Self confidence", "Prior Knowledge", "Distractions", "Motivation", "Summary of the Student during the week"]
for row in exam_activity_scores:
	if row in cspp_grades:
		tooltip = ""
		tooltip += cspp_grades[row].split('|')[0]+"[ExamScore, ActivityScore] = ["+str(float(exam_activity_scores[row][0]))+", "+str(float(exam_activity_scores[row][1]))+"]"
		tooltip += "\nEmail: "+ row+"\n\n"
		if " "+row in feedbacks:
			# print row
			# tooltip+="\n\nFeedback:\n"
			tooltip += feedback_headings[2]+": "+feedbacks[" "+row][2]+"\n"
			tooltip += feedback_headings[3]+": "+feedbacks[" "+row][3]+"\n"
			tooltip += feedback_headings[4]+": "+feedbacks[" "+row][4]+"\n"
			tooltip += feedback_headings[5]+": "+feedbacks[" "+row][5]+"\n"
			tooltip += feedback_headings[6]+": "+feedbacks[" "+row][6]+"\n"
			tooltip += feedback_headings[7]+": "+feedbacks[" "+row][7]+"\n"
			tooltip += feedback_headings[8]+": "+feedbacks[" "+row][8]+"\n"
			tooltip += feedback_headings[10]+": "+feedbacks[" "+row][10]+"\n"
			tooltip += feedback_headings[11]+": "+feedbacks[" "+row][11]+'\n'

		# print row
		# print tooltip
		print [float(exam_activity_scores[row][0]),float(exam_activity_scores[row][1]),cspp_grades[row].split('|')[1],tooltip,]
		# exam_activity_scores[row].append(cspp_grades[row])