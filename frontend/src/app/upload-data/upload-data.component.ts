import { Component, OnInit, Directive } from '@angular/core';
import { FileUploader } from 'ng2-file-upload';
import { APIService } from '../api.service';
import { ActivatedRoute } from '@angular/router';
import { ManagedSubs } from '../util/managed-subs';


@Component({
  selector: 'app-upload-data',
  templateUrl: './upload-data.component.html',
  styleUrls: ['./upload-data.component.css'],
})
export class UploadDataComponent extends ManagedSubs implements OnInit {
  public uploader:FileUploader = new FileUploader({url: ''});
  public hasBaseDropZoneOver:boolean = false;

  public collectionID: number = 0;

  constructor(private route : ActivatedRoute, private api : APIService) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
        this.collectionID = +params['id'];
        this.uploader.options.url = this.api.baseURL+'/collection/'+this.collectionID+'/upload';
      })
    );
  }

  public fileOverBase(e:any):void {
    this.hasBaseDropZoneOver = e;
  }

}
