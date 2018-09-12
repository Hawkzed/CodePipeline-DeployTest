import json
from PIL import Image, ImageFilter
import boto3
from botocore.exceptions import ClientError
import sys
import os
import io

def lambda_handler(event, context):

	for record in event['Records']:
		#prep filesystem, download file then process and upload
		s3Client = boto3.client(service_name='s3', region_name='eu-west-1')		
		bucket = record['s3']['bucket']['name']
		key = record['s3']['object']['key']
		downloadPath = "/tmp/" + key
		uploadPath = "/tmp/" + key
		
		os.makedirs("/tmp/input/", exist_ok = True)
		
		s3Client.download_file(bucket, key, downloadPath)
		blurImage(downloadPath, uploadPath)
		s3Client.upload_file(uploadPath, bucket, ("output" + key.lstrip("input")))
		
def blurImage(imagePath, editedPath):

	image = Image.open(imagePath) #open image using object from Pillow library
	
	rekogClient=boto3.client('rekognition')
	
	stream = io.BytesIO() #turn image into bytes to send off the the rekog server
	image.save(stream, format=image.format)
	imageBinary = stream.getvalue()
	
	try:
		response = rekogClient.detect_faces(Image = {'Bytes': imageBinary}, Attributes=["DEFAULT"])
	
		#print(response)
		convertedBoxList = []
		for faceDetail in response["FaceDetails"]:
			faceBoxList = [] #get the JSON information and take out the relevant parts
			faceBoxList.append(faceDetail["BoundingBox"].get("Width"))
			faceBoxList.append(faceDetail["BoundingBox"].get("Height"))
			faceBoxList.append(faceDetail["BoundingBox"].get("Left"))
			faceBoxList.append(faceDetail["BoundingBox"].get("Top"))
		
			convertedBoxList.append(convertToPixelLocation(faceBoxList, image.height, image.width))
			
			#[(left, top, right, bottom), (l,t,r,b)]
	
		for box in convertedBoxList: #Blurs out the face box
			imageCrop = image.crop(box)

			imageCrop = imageCrop.filter(ImageFilter.BoxBlur(box[3]/5))
				
			image.paste(imageCrop, box)
			
			image.save(editedPath)
		
	except ClientError as error:
		if error.response["Error"]["Code"] == "ResourceNotFoundException":
			print("The image was not found")
		else:
			print("Unexpected server error: " + error.response["Error"]["Message"])
	
def convertToPixelLocation(faceBoxList, imageHeight, imageWidth):
	
	#It starts of as a ratio of the image size, convert to co-rordinates (top and left) 
	#and length (width and height) by multiplying by the total width/height
	
	boxList = []
	for number in faceBoxList:
		if number > 1:
			boxList.append(1)
		elif number < 0:
			boxList.append(0)
		else:
			boxList.append(number)
	
	#width
	boxList[0] = imageWidth * boxList[0]
	#height
	boxList[1] = imageHeight * boxList[1]
	#left
	boxList[2] = imageWidth * boxList[2]
	#top
	boxList[3] = imageHeight * boxList[3]
	
	#top left
	#boxList[2])
	#boxList[3])
	#bottom right left + width, top + height
	#boxList[2] + boxList[0]
	#boxList[3] + boxList[1]
	box = ()
	box = (int(boxList[2]), int(boxList[3]), int(boxList[2] + boxList[0]),int(boxList[3] + boxList[1]))
		
	return(box)