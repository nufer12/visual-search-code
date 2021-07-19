export interface APIGenericDataItem {

}
export interface APIGenericDataFilter {
  
}

export interface Collection {
    id : number,
    name : string,
    creator: string,
    creator_id : number,
    created : string,
    comment : string,
    status : number,
    total_images : number,
    preview: string | null,
    editable: boolean
}

export interface UserData {
  coll_priv: number,
  id: number,
  name: string,
  collection_details: {
    [collID: number]: number
  }
  resource_priv : number,
  "session-id": string,
  time_limit: string,
  user_priv: number
}

export interface ImageData {
  id: number,
  filename: string,
  collection_id? : number,
  upload_date?: string,
  upload_username? : string,
  upload_user?: number,
  status? : number,
  orig_filename? : string,
  artist?: string,
  title?: string,
  date? : string,
  genre? : string,
  epoch? : string,
  measurements? : string,
  material?: string,
  technique? : string,
  institution? : string,
  provenienz?: string,
  iconclass?: string
}

export interface IndexData {
  id : number,
  is_latest: boolean,
  collection_id: number,
  creator_id: number,
  creator: string,
  creation_date: string,
  name: string,
  status: IndexStatus,
  exitcode: number,
  total_images: number,
  type: number,
  typename?: string,
  typedescription?: string
}

export enum IndexStatus {
  CANCEL_REQUESTED = -1,
  PENDING = 0,
  DELIVERED = 1,
  RUNNING = 2,
  STOPPED_WITH_ERRORS = 3,
  STOPPED_ON_REQUEST = 4,
  FINISHED = 5,
  DELETED = 9
}


export interface JobThread {
  name: string,
  status : string
}

export interface JobInfo {
  job_id : string,
  reg_time: number,
  start_time?: number,
  tot_time?: number,
  collection_id: number,
  index_id: number,
  search_id?: number,
  exit_code? : number
}

export interface EndpointJobs {
  running: JobInfo[],
  finished: JobInfo[],
  que: JobInfo[],
  workers: number
}

export type Bbox = number[];


export interface Search {
  id : number,
  name: string,
  index_id: number,
  collection_id: number,
  refined_search: string | null,
  base_search: number | null,
  creator_id: number,
  creator: string,
  creation_date: string,
  score: number,
  total_hits: number
  image_id: number,
  query_bbox: string,
  params: string,
  searchParams?: any,
  areas: Bbox[],
  status: number,
  exitcode: number,
  filename: string,
}

export interface SearchResult {
  box_data : string,
  areas: Bbox[],
  id : number,
  image_id: number,
  search_id: number,
  score: number,
  vote: number,
  total_boxes: number,
  searchParams? : any,
  filename : string,
  refined_searchbox: string,
  minscore: number,
  maxscore: number,
  tsne?: string
}

export interface Favorite {
  list: number[]
}

export interface Retrieval {
  id: number,
  image_id: number,
  search_id: number,
  score: number,
  vote: number,
  total_boxes: number,
  box_data: string,
  areas : Bbox[],
  filename: string,

  query_image_id: number,
  query_bbox: string,
  query_filename: string,
  refined_searchbox: string,
  minscore: number,
  maxscore: number
}

export interface IndexType {
  id: number,
  name: string,
  description: string
}

export interface Worker {
  id: number,
  current_job: number,
  status: number,
  last_update: string,
  type: number,
  description: string
}
export interface Job {
  id: number,
  collection_id: number,
  type: number,
  creator_id: number,
  start_time: string,
  end_time: string,
  exitcode: number,
  status: number
}