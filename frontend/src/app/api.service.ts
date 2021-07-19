import { Injectable, OnDestroy } from '@angular/core';
import { Observable, Subject} from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { Retrieval, ImageData, Collection, UserData, EndpointJobs, SearchResult, Bbox, IndexData, Search, Job, Favorite, IndexType, Worker } from './util/data-types';
import { Router } from '@angular/router';
import { NotificationService } from './notification.service';
import { RemoteDataStructureList, RemoteDataStructureListSliceable } from './util/remote-data';
import { Md5 } from 'ts-md5';
import { resolve } from 'url';


@Injectable({
  providedIn: 'root'
})
export class APIService {

  public baseURL = '/api';
  // public baseURL = 'http://localhost:80/api';


  public token = '';
  
  public data : {[id: string]: RemoteDataStructureList<any>} = {};
  public user : UserData;

  public isAuthenticated : Subject<boolean> = new Subject();

  constructor(private notifier : NotificationService, private http: HttpClient, private router : Router) {
    this.token = localStorage.getItem('SESSION_ID');

    this.data['user'] = new RemoteDataStructureList<UserData>(this).setURL('/auth/check');
    this.data['user_man'] = new RemoteDataStructureList<UserData[]>(this).setURL('/user/:id/info');
    
    this.data['indices'] = new RemoteDataStructureList<IndexData[]>(this).setURL('/collection/:id/indices');
    this.data['threads'] = new RemoteDataStructureList<string[]>(this).setURL('/jobserver/threads');
    this.data['indexJobs'] = new RemoteDataStructureList<EndpointJobs[]>(this).setURL('/jobserver/indices');
    this.data['searchJobs'] = new RemoteDataStructureList<EndpointJobs[]>(this).setURL('/jobserver/searches');
    this.data['indexTypes'] = new RemoteDataStructureListSliceable<IndexType[]>(this).setURL('/collection/:id/indices/types');
    

    this.data['searchSiblings'] = new RemoteDataStructureList<Search[]>(this).setURL('/search/:id/siblings');
    this.data['searchRelated'] = new RemoteDataStructureListSliceable<Search[]>(this).setURL('/search/:id/related');
    this.data['searchFavorites'] = new RemoteDataStructureListSliceable<number[]>(this).setURL('/search/:id/favorites');
    this.data['searches'] = new RemoteDataStructureListSliceable<Search[]>(this).setURL('/collection/:id/searches');
    this.data['images'] = new RemoteDataStructureListSliceable<ImageData[]>(this).setURL('/collection/:id/images');
    this.data['imageSearches'] = new RemoteDataStructureListSliceable<Search[]>(this).setURL('/image/:id/searches');
    this.data['imageRetrievals'] = new RemoteDataStructureListSliceable<Search[]>(this).setURL('/image/:id/retrievals');
    this.data['collections'] = new RemoteDataStructureListSliceable<Collection[]>(this).setURL('/collection/all/list');
    this.data['trashImages'] = new RemoteDataStructureListSliceable<ImageData[]>(this).setURL('/collection/:id/images');
    this.data['searchResults'] = new RemoteDataStructureListSliceable<SearchResult[]>(this).setURL('/search/:id/results');
    this.data['users'] = new RemoteDataStructureListSliceable<{id: number, name: string}[]>(this).setURL('/user/all/list');

    this.data['user'].get().subscribe(
      data => {
        if(data != null) {
          this.user = data.data;
        }
      }
    );
  }

  clearCache() {
    this._processResponse(
      this.requestPost<boolean>('/auth/clearcache', {}, {}, {}),
      'Cache cleared.',
      {}
    ).then(_ => {
      for(let list of Object.values(this.data)) {
        list.refreshAll();
      }
    })
  }


  checkAuthError(error) {
    if(error.status == 401) {
      this.isAuthenticated.next(false);
    }
  }

  public requestGet<T>(url : string, urlParams : {[key: string]: string}, getParams : {[key: string]: string}) : Observable<T> {
    return Observable.create(observer => {
      //if(this.token != null) {
      //  getParams['token'] = this.token;
      //}
      let getParameters = Object.assign({token: this.token}, getParams);
      let requestURL = this.baseURL + url;
      for(let param in urlParams) {
        requestURL = requestURL.replace(new RegExp('\/:'+param+'($|\/)'), '/'+urlParams[param]+'$1');
      }
      console.log("Hello world 2", this.router.url);
      console.log("Hello world", requestURL);
      this.http.get(requestURL, {params: getParameters}).subscribe(
        data => {
          observer.next(data as T);
        }, error => {
          // this.redirectToLoginOnAuthError(error);
          console.log("ERROR requestGet", error);
          this.notifier.failed(error.error.message);
          this.checkAuthError(error);
          observer.error(error);
        }
      )
    })
  }

  public requestPost<T>(url, urlParams : {[key: string]: string}, bodyParams : Object, getParams : {[key: string] : string} ) : Observable<T> {
    return Observable.create(observer => {
      if(this.token != null) {
        getParams['token'] = this.token;
      }
      let requestURL = this.baseURL + url;
      for(let param in urlParams) {
        requestURL = requestURL.replace(new RegExp('\/:'+param+'($|\/)'), '/'+urlParams[param]+'$1');
      }
      this.http.post(requestURL, bodyParams, {params: getParams}).subscribe(
        data => {
          observer.next(data as T);
        }, error => {
          console.log("ERROR requestPost", error);
          this.notifier.failed(error.error.message);
          this.checkAuthError(error);
          observer.error(error);
        }
      )
    })
  }

  private _processResponse<T>(p : Observable<T>, message : string, to_update : {[name: string]: number} = {}) : Promise<T> {
    return new Promise((resolve, reject) => {
      p.subscribe(
        data => {
          Object.keys(to_update).forEach((name) => {
            this.data[name].refresh(to_update[name]);
          });
          this.notifier.success(message);
          resolve(data);
        }, error => {
          this.notifier.failed(error);
          reject(error);
        }
      )
    })
  }

  private _subscriptionStorage : {[id: string]: Observable<any>} = {};
  public getDataByID<T>(dataKey: string, apiKey: number, elementID: number) : Observable<any> {
    let completeKey = dataKey + '-' + elementID;
    if(!this._subscriptionStorage[completeKey]) {
      this._subscriptionStorage[completeKey] = new Observable(observer => {
        this.data[dataKey].get(apiKey).subscribe(data => {
          if(data) {
            let searched = data.data.filter(el => {
              return el.id == elementID;
            });
            if(searched.length > 0) {
              observer.next(searched[0]);
            }
          }
        })
      })
    }
    return this._subscriptionStorage[completeKey];
  }

  /*


  Authentication


  */

  login(username : string, password: string) : Promise<boolean> {
    let hashed_pass = Md5.hashStr(password);
    let timestamp = ''+(new Date).getTime();
    let hash = ''+Md5.hashStr(hashed_pass + timestamp);
    return new Promise((resolve, reject) => {
      this.requestPost<UserData>('/auth/login', {}, {username: username, password: hash, time: timestamp}, {}).subscribe(
        data => {
          this.token = data['session-id'];
          localStorage.setItem('SESSION_ID', data['session-id']);
          window.location.reload();
        }, error => {
          console.log('ERROR DataService login');
        }
      );
    })
  }

  logout() : Promise<boolean> {
    return new Promise((resolve, reject) => {
      this.token = '';
      localStorage.removeItem('SESSION_ID');
      this.requestGet<boolean>('/auth/logout', {}, {}).subscribe(res => {
        console.log(res);
        resolve(true);
      });
    })
  }

  


  /*


  Collections


  */

  createCollection(title : string, comment : string) : Promise<Collection> {
    return this._processResponse(
      this.requestPost<Collection>('/collection/all/new', {}, {title: title, comment: comment}, {}),
      'Collection created.',
      {'collections': 0}
    )
  }

  updateCollection(collectionID : number, data : {[key: string]: string}) : Promise<boolean> {
    return this._processResponse(
      this.requestPost<boolean>('/collection/:id/update', {id: ''+collectionID}, data, {}),
      'Updated Collection '+collectionID+'.',
      {'collections': 0}
    )
  }

  removeCollection(collectionID : number) : Promise<boolean> {
    return this._processResponse(
      this.requestGet<boolean>('/collection/:id/remove', {id: ''+collectionID}, {}),
      'Removed Collection '+collectionID+'.',
      {'collections': 0}
    )
  }

  recoverCollection(collectionID : number) : Promise<boolean> {
    return this._processResponse(
      this.requestGet<boolean>('/collection/:id/recover', {id: ''+collectionID}, {}),
      'Recovered Collection '+collectionID+'.',
      {'collections': 0}
    )
  }

  upload(collectionID : number, file : any, relativePath : any) : Promise<boolean> {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', file, relativePath);
      this.http.post<any>(this.baseURL+'/collection/'+collectionID+'/upload?token='+this.token, formData).subscribe(data => {
        resolve(true);
      }, error => {
        console.log("DataService ERROR uploadImage: ", error);
        reject(error.status);
        // this.redirectToLoginOnAuthError(error);
      });
    })
  }

  /*


  Images


  */

  getImageInfo(imageID : number) : Observable<ImageData> {
    return this.requestGet<ImageData>('/image/:id/info', {id: ''+imageID}, {});
  }

  deleteImage(imageID : number, collectionID : number) : Promise<boolean> {
    return this._processResponse(
      this.requestGet<boolean>('/image/:id/remove', {id: ''+imageID}, {}),
      'Removed Image '+imageID+'.',
      {'images': collectionID, 'trashImages': collectionID}
    );
  }

  recoverImage(imageID : number, collectionID: number) : Promise<boolean> {
    return this._processResponse(
      this.requestGet<boolean>('/image/:id/recover', {id: ''+imageID}, {}),
      'Recovered Image '+imageID+'.',
      {'images': collectionID, 'trashImages': collectionID}
    );
  }

  updateImage(imageID : number, data : {[key: string]: string}) : Promise<boolean> {
    return this._processResponse(
      this.requestPost<boolean>('/image/:id/update', {id: ''+imageID}, data, {}),
      'Updated Image '+imageID+'.'
    )
  }


  /*


  Indices


  */

  createIndex(collectionID : number, title: string, indexType: number, indexMachine: number) : Promise<boolean> {
    return this._processResponse<boolean>(
      this.requestPost<boolean>('/collection/:id/indices/create', {id: ''+collectionID}, {title: title, indextype: indexType, machine: indexMachine}, {}),
      'Index created.',
      {'indices': collectionID}
    )
  }


  // startIndexing(collectionID : number, indexID : number, type : string = 'run') : Promise<boolean> {
  //   return this._processResponse<boolean>(
  //     this.requestGet<boolean>('/index/:id/'+type, {id: ''+indexID}, {}),
  //     'Index started.',
  //     {'indices': collectionID}
  //   )
  // }

  rerunIndex(collectionID: number, indexID: number) : Promise<boolean> {
    return this._processResponse<boolean>(
      this.requestGet<boolean>('/index/:id/rerun', {id: ''+indexID}, {}),
      'Index rerunning.',
      {'indices': collectionID}
    )
  }

  cancelIndexing(collectionID : number, indexID : number) : Promise<boolean> {
    return this._processResponse<boolean>(
      this.requestGet<boolean>('/index/:id/stop', {id: ''+indexID}, {}),
      'Index stopped.',
      {'indices': collectionID}
    )
  }

  getUnreviewed(collectionID : number, indexIDs : string[], searchIDs : string[], maxRetrievals : number) : Observable<Retrieval[]> {
    return this.requestGet<Retrieval[]>('/collection/:id/searches/review', {id: ''+collectionID}, {"search": searchIDs.join(','), "index": indexIDs.join(','), "max_retrievals": ''+maxRetrievals});
  }

  updateIndex(collectionID: number, indexID : number, newName: string) : Promise<boolean> {
    return this._processResponse(
      this.requestPost<boolean>('/index/:id/update', {id: ''+indexID}, {name: newName}, {}),
      'Updated Index '+indexID+'.',
      {'indices': collectionID}
    )
  }

  /*


  Searches


  */


  voteForResult(resID : number, vote : number) : Promise<number> {
    return this._processResponse(
      this.requestPost<number>('/searchresult/:id/vote', {id: ''+resID}, {vote: ''+vote}, {}),
      'Voted search result '+resID+'.'
    )
  }

  changeRefinementBox(resID : number, newBoxData : number[][]) : Promise<boolean> {
    return this._processResponse(
      this.requestPost<boolean>('/searchresult/:id/refine', {id: ''+resID}, {refinement: JSON.stringify(newBoxData)}, {}),
      'Updated refinement for '+resID+'.'
    );
  }

  startSearch(collectionID: number, imageID : number, indexID : number, searchBoxes : any, combination: string, geomWeight : number[], name : string, relatedID : number = null) : Promise<number> {
    let refreshDict = {
      'searches': collectionID
    }
    if(relatedID) {
      refreshDict['searchRelated'] = relatedID
    }
    return this._processResponse<number>(
      this.requestPost<number>('/index/:id/searches/create', {id: ''+indexID}, {image_id: ''+imageID, search_boxes: JSON.stringify(searchBoxes), params: {"combination": combination, "weights": geomWeight}, name: name, related: relatedID}, {}),
      'Started search.',
      refreshDict,
    )
  }

  refineSearch(collectionID: number, searchID: number) : Promise<number> {
    return this._processResponse<number>(
      this.requestGet<number>('/search/:id/refine', {id: ''+searchID}, {}),
      'Started search.',
      {'searches': collectionID},
    )
  }

  updateSearch(collectionID, searchID: number, values : {[key: string]: string}) : Promise<boolean> {
    return this._processResponse<boolean>(
      this.requestPost<boolean>('/search/:id/update', {id: ''+searchID}, values, {}),
      'Updated search.',
      {'searches': collectionID}
    )
  }

  _getCurrentFavorites(searchID, cache = true) : Promise<number[]> {
    return new Promise((resolve, reject) => {
      this.data["searchFavorites"].get(searchID, cache).subscribe(
        result => {
          if(result) {
            resolve(result.data);
          }
        }, error => {
          reject(error);
        }
      )
    })
  }

  updateFavorites(searchID: number, favorite_list) : Promise<void> {
    return this._processResponse(
      this.requestPost<void>('/search/:id/favorites/update', {id: ''+searchID}, {'new_favorites': favorite_list}, {}),
      'Updated Favorites',
      {'searchFavorites': searchID}
    )
  }

  


  /*


  Resources


  */

  modifyServerState(state : string) : Promise<boolean> {
    return this._processResponse<boolean>(
      this.requestGet<boolean>('/jobserver/:state', {state: state}, {}),
      'Job server '+state,
      {'threads': 0, 'indexJobs': 0},
      // {'threads': 0, 'indexJobs': 0, 'searchJobs': 0},
    )
  }

  setWorkers(endpoint : string, num : number) : Promise<boolean> {
    return this._processResponse<boolean>(
      this.requestPost<boolean>('/jobserver/workers', {}, {endpoint: endpoint, num: ''+num}, {}),
      'Updated number of workers',
      {'threads': 0, 'indexJobs': 0},
      // {'threads': 0, 'indexJobs': 0, 'searchJobs': 0},
    )
  }


  getWorkers() : Observable<Worker[]> {
    return this.requestGet<Worker[]>('/job/0/info', {}, {});
  }

  getJobs(which: string) : Observable<Job[]> {
    return this.requestGet<Job[]>('/job/0/:which', {which: which}, {});
  }

  cancelJob(id: number, type: number) {
    return this._processResponse<boolean>(
      this.requestGet<boolean>('/job/:id/cancel/:type', {id: ''+id, type: ''+type}, {}),
      'Canceld Job '+id+'.',
      {}
    )
  }


  updateUser(userID : number, data : Object) : Promise<boolean> {
    return this._processResponse(
      this.requestPost<boolean>('/user/:id/update', {id: ''+userID}, data, {}),
      'Updated User '+userID+'.',
      {'user_man': userID, 'users': 0}
    )
  }

  createUser(name, password) : Promise<number> {
    return this._processResponse(
      this.requestPost<number>('/user/all/new', {}, {name: name, password: password}, {}),
      'Created User.',
      {'users': 0}
    )
  }



}
