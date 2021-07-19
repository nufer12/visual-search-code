import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  constructor() { }
  public message : Subject<{msg: string, type: string}> = new Subject();
  alert(msg: string, type: string) {
    this.message.next({
      msg: msg,
      type: type
    });
  }
  success(msg: string) {
    this.alert(msg, 'success');
  }
  failed(msg: string) {
    this.alert(msg, 'danger');
  }
}