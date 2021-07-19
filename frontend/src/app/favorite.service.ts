import { Injectable } from '@angular/core';
import { APIService } from './api.service';
import { BehaviorSubject } from 'rxjs';
import { SearchResult, Search } from './util/data-types';
import { Subscriptable } from './util/managed-subs';

@Injectable({
  providedIn: 'root'
})
export class FavoriteService {

  public isDragging : boolean = false;

  constructor(private api: APIService) {

  }

  private _local : {[id: number]: number[]} = {};
  private _subs : {[id: number]: Subscriptable} = {};

  public localChanges = new BehaviorSubject(null);

  getData(searchID : number) : Promise<number[]> {
    return new Promise((resolve, reject) => {
      if(!this._subs[searchID]) {
        this._local[searchID] = [];
        this._subs[searchID] = this.api.data["searchFavorites"].get(searchID).subscribe(data => {
          if(data) {
            this._local[searchID] = data.data;
            this.localChanges.next(true);
            resolve(data.data);
          }
        });
      } else {
        resolve(this._local[searchID]);
      }
    });
  }

  isFavorite(resID: number, searchID: number) : Promise<boolean> {
    return new Promise((resolve, reject) => {
      this.getData(searchID).then(
        data => {
          if(data.indexOf(resID) > -1) {
            resolve(true);
          } else {
            resolve(false);
          }
        }
      )
    })
  }

  reorder(searchID: number, dropTarget: number, dropped: number) {
    this.getData(searchID).then(data => {
      if(data) {
        let newOrder = [];
        data.forEach(element => {
          if(element == dropTarget) {
            newOrder.push(dropped);
          }
          if(element != dropped) {
            newOrder.push(element)
          }
        });
        this.api.updateFavorites(searchID, newOrder).then(() => {
          console.log('update order');
        });
      }
    });
  }

  removeFavorite(resID : number, searchID: number) : Promise<void> {
    return new Promise((resolve, reject) => {
      this.getData(searchID).then(data => {
        if(data) {
          let new_favorites = data.filter(el => {
            return el != resID;
          });
          this.api.updateFavorites(searchID, new_favorites).then(() => {
            resolve();
          });
        }
      });
    })
  }

  addFavorite(resID : number, searchID: number) : Promise<void> {
    return new Promise((resolve, reject) => {
      this.getData(searchID).then(data => {
        if(data) {
          let new_favorites = data.filter(el => {
            return el != resID;
          });
          new_favorites.push(resID);
          this.api.updateFavorites(searchID, new_favorites).then(() => {
            resolve();
          });
        }
      });
    })
  }

}
