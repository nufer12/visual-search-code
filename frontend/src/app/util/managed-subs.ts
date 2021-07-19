import { OnDestroy } from '@angular/core';
export interface Subscriptable {
  subscribe?: (data) => void;
  unsubscribe: () => void
}
export class ManagedSubs implements OnDestroy {
  protected subs : {[key: string]: Subscriptable} = {};
  manageSub(key: string, sub : Subscriptable) {
    if(this.subs[key] != undefined) {
      this.subs[key].unsubscribe();
    }
    this.subs[key] = sub;
  }
  unsubscribeAll() {
    for(let sub in this.subs) {
      this.subs[sub].unsubscribe();
    }
  }
  ngOnDestroy() {
    this.unsubscribeAll();
  }
}