import os.path,subprocess
from subprocess import STDOUT,PIPE
import sys
import os.path
import hashlib
import base64
# import crypt
os.environ['http_proxy'] = ''
import urllib2, urllib

def which_python():
    if (sys.version_info > (3, 0)):
        return 3
    else:
        return 2

python_version = which_python()

def computeMD5hash(stringg):
    m = hashlib.md5()
    if python_version == 2:
        m.update(stringg.encode('utf8'))
    else:
        m.update(stringg)
    return m.hexdigest()

def get_content(filename):
    with open(filename, "rb") as f:
        content = f.read()
    return open(filename, "rb")

def execute(file, stdin):
    filename,ext = os.path.splitext(file)
    if ext == ".java":
        subprocess.check_call(['javac', "*.java"])     #compile
        cmd = ['java', "Solution"]                     #execute
    elif ext == ".c":
        subprocess.check_call(['gcc',"-o","Solution","Solution.c"])     #compile
        cmd = ['./Solution']                     #execute
    else:
        cmd = ['python', file]

    proc = subprocess.Popen(cmd, stdout=subprocess.STDOUT, stdin=stdin, stderr=subprocess.STDOUT)
    stdout,stderr = proc.communicate(stdin)
    return stdout

def run_test(testcase_input,testcase_output):
    input = get_content(testcase_input)
    # input = open(testcase_input,"r")
    # md5input = get_content("md5/"+testcase_input)
    output = get_content(testcase_output)
    # md5output = get_content("md5/"+testcase_output)
    your_output = execute(program_name, input)

    # if python_version == 3:
        # md5input = md5input.decode('utf-8')
        # md5output = md5output.decode('utf-8')

    # if computeMD5hash(input) != md5input or computeMD5hash(output) != md5output:
        # print(computeMD5hash(input),crypt.computeMD5hash1(input),computeMD5hash(output),crypt.computeMD5hash1(output))
        # return False

    if python_version == 3:
        your_output = your_output.decode('UTF-8').replace('\r','').rstrip() #remove trailing newlines, if any
        output = output.decode('UTF-8').replace('\r','').rstrip()
    else:
        your_output = your_output.replace('\r','').rstrip() #remove trailing newlines, if any
        output = output.replace('\r','').rstrip()

    return input,output,your_output,output==your_output

def run_tests(inputs,outputs,extension):
    passed = 0
    for i in range(len(inputs)):
        result = run_test(inputs[i],outputs[i])
        if result == False:
            print("########## Testcase "+str(i)+": Failed ##########")
            print("Something is wrong with the testcase.\n")
        elif result[3] == True:
            print("########## Testcase "+str(i)+": Passed ##########")
            print("Expected Output: ")
            print(result[1]+"\n")
            print("Your Output: ")
            print(result[2]+"\n")
            passed+=1
        else:
            print("########## Testcase "+str(i)+": Failed ##########")
            print("Expected Output: ")
            print(result[1]+"\n")
            print("Your Output: ")
            print(result[2]+"\n")
        print("----------------------------------------")
    print("Result: "+str(passed)+"/"+str(len(inputs))+" testcases passed.")


if len(sys.argv)==4 and os.path.isfile(sys.argv[1]):
    inputs = []
    outputs = []

    # populate input and output lists
    testcases_folder = sys.argv[2]

    for root,dirs,files in os.walk(testcases_folder):
        for file in files:
            if 'input' in file and '.txt' in file:
                inputs.append(testcases_folder+"/"+file)
            if 'output' in file and '.txt' in file:
                outputs.append(testcases_folder+"/"+file)
        break

    inputs = sorted(inputs)
    outputs = sorted(outputs)

    if sys.argv[1].endswith(".java"):
        program_name = sys.argv[1]
        extension = ".java"
        run_tests(inputs,outputs,extension)
    elif sys.argv[1].endswith(".py"):
        program_name = sys.argv[1]
        extension = ".py"
        run_tests(inputs,outputs,extension)
    elif sys.argv[1].endswith(".c"):
        program_name = sys.argv[1]
        extension = ".c"
        run_tests(inputs,outputs,extension)
    elif sys.argv[1] == "testcase_eval.py":
        print("eval.py cannot be passed as argument")
    else:
        print("Invalid Extension.\nPass only .java or .py files")
else:
    print("File not found.\nPass a valid filename with extension as argument.\npython eval.py <filename>")
