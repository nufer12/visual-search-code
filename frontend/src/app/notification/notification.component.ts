import { Component, OnInit } from '@angular/core';
import { NotificationService } from '../notification.service';

@Component({
  selector: 'app-notification',
  templateUrl: './notification.component.html',
  styleUrls: ['./notification.component.scss']
})
export class NotificationComponent implements OnInit {

  private notSub : any;
  public currMsg : {msg: string, type: string}[] = [];

  constructor(private notifier : NotificationService) {
    this.notSub = notifier.message.subscribe(
      message => {
        if(message.msg != "") {
          this.notify(message);
        }
      }
    )
  }

  notify(msg : {msg: string, type: string}) {
    this.currMsg.push(msg);
    let self = this;
    setTimeout(function() {
      self.currMsg = self.currMsg.filter(obj => obj !== msg);
    }, 6000);
  }

  ngOnInit() {
  }

  ngOnDestroy() {
    this.notSub.unsubscribe();
  }

}
