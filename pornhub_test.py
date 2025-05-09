from pornhub_api import PornhubApi
api = PornhubApi()
# video = api.video.get_by_id("ph560b93077ddae")
# print(type(video))
# video_data = video.dict()
# print(type(video_data['video']))
# print(video_data['video']['title'])
# print(video_data['video']['url'])

# print(type(api.search))

video_data = api.video.categories
print(type(video_data))