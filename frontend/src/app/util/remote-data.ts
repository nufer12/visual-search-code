import { Observable, BehaviorSubject } from 'rxjs';
import { APIService } from '../api.service';

export class RemoteDataStructureList<T> {
    public url : string;
    public regex = /\/:id($|\/)/g;
    protected _list : {[id : number]: BehaviorSubject<{data: T, total: number}>} = {};
    protected _parameters : {[id: number]: {[key: string]: string}} = {};

    constructor(private api: APIService) {
    }

    public setURL(url: string) : RemoteDataStructureList<T> {
        this.url = url;
        return this
    }

    public refresh(id: number = 0, params : {[key: string]: string} = {}) : BehaviorSubject<{data: T, total: number}> {
      if(this._list[id] == null) {
        this._list[id] = new BehaviorSubject(null);
      } else {
        this._list[id].next(null);
      }
      this._parameters[id] = params;
      this.api.requestGet<{data: T, total: number}>(this.url, {'id': ''+id}, params).subscribe(
        data => {
          this._list[id].next(data as {data: T, total: number});
        }, error => {
          console.log("RemoteDataStructureList ERROR refresh: ", error);
          this._list[id].error(error);
        }
      );
      return this._list[id];
    }
  
    public refreshAll() {
      Object.keys(this._list).forEach(el => {
        this.refresh(+el);
      })
    }
  
    public get(id : number = 0, cache = true, params : {[key: string]: string} = {}) : BehaviorSubject<{data: T, total: number}> {
      let haveData = this._list[id] != null && this._parameters[id] != null && cache;
      let sameParameters = true;
      if(haveData) {
        sameParameters = JSON.stringify(params) === JSON.stringify(this._parameters[id])
      }
      if(haveData && sameParameters) {
        console.log('GOOD NEWS: got from cache', this.url);
        return this._list[id];
      } else {
        console.log('BAD NEWS: need refresh', this.url);
        return this.refresh(id, params);
      }
    }
  
    public next(data: {data: T, total: number}, id: number = 0) {
      if(this._list[id] == null) {
        this._list[id] = new BehaviorSubject(null);
      }
      this._list[id].next(data);
    }
    public error(error : any, id: number = 0) {
      this._list[id].error(error);
    }
  }
  
  export class RemoteDataStructureListSliceable<T> extends RemoteDataStructureList<T> {
    public buffer = 50;
    public getSlice(id : number = 0, from : number = 0, to : number = 0, params : {[key: string]: string} = {}) : Observable<{data: T, total: number}> {
      let oldParams = this._parameters[id];
      let isInBuffer = oldParams != null && oldParams.from != null && (+oldParams.from <= from - this.buffer || +oldParams.from == 0 ) && oldParams.to != null && to + this.buffer <= +oldParams.to;
      if(isInBuffer) {
        params['from'] = oldParams.from;
        params['to'] = oldParams.to;
      } else {
        params['from'] = ''+Math.max(0, from - 3*this.buffer);
        params['to'] = ''+(to + 3*this.buffer);
      }

      return Observable.create(observer => {
        this.get(id, true, params).subscribe(data => {
          if(data != null) {

            let start = from - +params['from'];
            let end = start + to - from;

            let cutOutData = Array.prototype.slice.call(data.data, start, end);
            observer.next({data: cutOutData, total: data.total});
          }
        })
      })
    }
  }